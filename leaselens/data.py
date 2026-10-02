"""Area statistics: median rent / income by ZIP, plus cheaper nearby ZIPs.

Contract (agreed between Person A and Person B):
    get_area_stats(zip_code) -> {
        "zip": str, "median_rent": int, "median_income": int, "year": str,
        "place": str, "source": "snowflake" | "mock",
        "nearby": [{"zip", "median_rent", "miles", "place"}, ...]  # cheapest first
    }

Uses Snowflake when credentials exist in .streamlit/secrets.toml (or env vars),
otherwise falls back to data/mock_area_stats.csv so the UI works offline.
"""
from __future__ import annotations

import csv
import math
import os
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOCK_CSV = ROOT / "data" / "mock_area_stats.csv"
AREA_SQL = ROOT / "sql" / "02_area_stats.sql"
CENTROIDS_CSV = ROOT / "data" / "zcta_centroids.csv"
# Snapshot of the Snowflake query result. Written after every live load, or saved by hand
# from Snowsight (Download -> CSV). Lets the demo run with no network or login.
SNAPSHOT_CSV = ROOT / "data" / "area_stats_snowflake.csv"
# Ignore "nearby" ZIPs whose median is under this share of yours (e.g. tribal or
# subsidized-housing areas whose medians aren't comparable market rents).
MIN_COMPARABLE_SHARE = 0.6
NEARBY_RADIUS_MILES = 8


def haversine_miles(lat1, lon1, lat2, lon2) -> float:
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# ---------- data sources -------------------------------------------------

def _year_key(year: str) -> int:
    """'2024', '2020–2024 ACS 5-year' -> 2024 (the last 4-digit number)."""
    nums = re.findall(r"\d{4}", str(year))
    return int(nums[-1]) if nums else 0


def _latest_per_zip(rows: list[dict]) -> list[dict]:
    """Keep one row per ZIP (the newest year with a rent value). Lets the app accept
    exports that include every year, e.g. CoCo's 2011-2024 history."""
    best: dict[str, dict] = {}
    for r in rows:
        if r["median_rent"] is None:
            continue
        cur = best.get(r["zip"])
        if cur is None or _year_key(r["year"]) > _year_key(cur["year"]):
            best[r["zip"]] = r
    for r in best.values():
        y = _year_key(r["year"])
        if r["year"].isdigit() and y:          # plain '2024' -> '2020–2024 ACS 5-year'
            r["year"] = f"{y - 4}–{y} ACS 5-year"
    return sorted(best.values(), key=lambda r: r["zip"])


def _load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return _fill_centroids(_latest_per_zip([_coerce(r) for r in csv.DictReader(f)]))


def _save_snapshot(rows: list[dict]) -> None:
    cols = ["zip", "place", "median_rent", "median_income", "year", "lat", "lon"]
    with open(SNAPSHOT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows({c: r[c] for c in cols} for r in rows)


def _coerce(r: dict) -> dict:
    """Normalize a row from any source to plain Python types."""
    r = {k.lower().strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
    r = {k: (None if isinstance(v, str) and v.upper() in ("NULL", "NONE", "NAN") else v) for k, v in r.items()}
    return {
        "zip": str(r["zip"]).zfill(5),
        "place": r.get("place") or "",
        "median_rent": int(float(r["median_rent"])) if r.get("median_rent") not in (None, "") else None,
        "median_income": int(float(r["median_income"])) if r.get("median_income") not in (None, "") else None,
        "year": str(r.get("year") or ""),
        "lat": float(r["lat"]) if r.get("lat") not in (None, "") else None,
        "lon": float(r["lon"]) if r.get("lon") not in (None, "") else None,
    }


def _snowflake_config() -> dict | None:
    """Read credentials from Streamlit secrets or environment variables."""
    cfg = None
    try:
        import streamlit as st  # noqa: WPS433
        if "snowflake" in st.secrets:
            cfg = dict(st.secrets["snowflake"])
    except Exception:
        cfg = None
    if not cfg and os.getenv("SNOWFLAKE_ACCOUNT"):
        cfg = {k: os.getenv(f"SNOWFLAKE_{k.upper()}") for k in
               ("account", "user", "password", "warehouse", "database", "schema", "role")}
        cfg = {k: v for k, v in cfg.items() if v}
    return cfg or None


def _load_snowflake(cfg: dict) -> list[dict]:
    """Run sql/02_area_stats.sql, which must return one row per ZIP with columns
    ZIP, PLACE, MEDIAN_RENT, MEDIAN_INCOME, YEAR, LAT, LON."""
    import snowflake.connector

    sql = AREA_SQL.read_text(encoding="utf-8")
    conn = snowflake.connector.connect(**cfg)
    try:
        cur = conn.cursor(snowflake.connector.DictCursor)
        cur.execute(sql)
        rows = [_coerce(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return _fill_centroids(_latest_per_zip(rows))


def _fill_centroids(rows: list[dict]) -> list[dict]:
    """Fill missing LAT/LON from data/zcta_centroids.csv (columns: zip,lat,lon).
    Build it from the Census Gazetteer ZCTA file; see docs/SNOWFLAKE_SETUP.md."""
    if not CENTROIDS_CSV.exists():
        return rows
    with open(CENTROIDS_CSV, newline="", encoding="utf-8") as f:
        cents = {r["zip"].zfill(5): (float(r["lat"]), float(r["lon"])) for r in csv.DictReader(f)}
    for r in rows:
        if r["lat"] is None and r["zip"] in cents:
            r["lat"], r["lon"] = cents[r["zip"]]
    return rows


@lru_cache(maxsize=1)
def load_table() -> tuple[tuple[dict, ...], str]:
    """Load every ZIP once per session. Returns (rows, source).
    Order: live Snowflake -> saved Snowflake snapshot -> mock data."""
    cfg = _snowflake_config()
    if cfg:
        try:
            rows = _load_snowflake(cfg)
            _save_snapshot(rows)
            return tuple(rows), "snowflake"
        except Exception as e:  # keep the demo alive if the network dies
            print(f"[leaselens] Snowflake failed, falling back: {e}")
    if SNAPSHOT_CSV.exists():
        return tuple(_load_csv(SNAPSHOT_CSV)), "snowflake-snapshot"
    return tuple(_load_csv(MOCK_CSV)), "mock"


# ---------- public API ---------------------------------------------------

def get_area_stats(zip_code: str, radius_miles: float = NEARBY_RADIUS_MILES) -> dict | None:
    rows, source = load_table()
    zip_code = str(zip_code).strip().zfill(5)
    by_zip = {r["zip"]: r for r in rows}
    me = by_zip.get(zip_code)
    if not me or me["median_rent"] is None:
        return None

    nearby = []
    if me["lat"] is not None:
        for r in rows:
            if r["zip"] == zip_code or r["median_rent"] is None or r["lat"] is None:
                continue
            if r["median_rent"] < me["median_rent"] * MIN_COMPARABLE_SHARE:
                continue
            d = haversine_miles(me["lat"], me["lon"], r["lat"], r["lon"])
            if d <= radius_miles:
                nearby.append({"zip": r["zip"], "place": r["place"],
                               "median_rent": r["median_rent"], "miles": round(d, 1),
                               "lat": r["lat"], "lon": r["lon"]})
    nearby.sort(key=lambda n: n["median_rent"])

    return {
        "zip": zip_code, "place": me["place"],
        "median_rent": me["median_rent"], "median_income": me["median_income"],
        "year": me["year"], "source": source, "nearby": nearby,
        "lat": me["lat"], "lon": me["lon"],
    }


def rent_vs_median(rent: float, median_rent: float) -> float:
    """Percent above (+) or below (-) the area median."""
    return round((rent - median_rent) / median_rent * 100, 1)
