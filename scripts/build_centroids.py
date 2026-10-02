#!/usr/bin/env python3
"""Build data/zcta_centroids.csv (zip,lat,lon) from the Census Gazetteer ZCTA file.

1. Download the "ZIP Code Tabulation Areas" Gazetteer file from
   https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html
2. Unzip it, then:  python scripts/build_centroids.py 2024_Gaz_zcta_national.txt
"""
import csv
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "zcta_centroids.csv"

if len(sys.argv) != 2:
    sys.exit(__doc__)
with open(sys.argv[1], encoding="utf-8") as f, open(OUT, "w", newline="", encoding="utf-8") as out:
    reader = csv.DictReader(f, delimiter="\t")
    reader.fieldnames = [h.strip() for h in reader.fieldnames]
    w = csv.writer(out)
    w.writerow(["zip", "lat", "lon"])
    n = 0
    for r in reader:
        w.writerow([r["GEOID"].strip(), r["INTPTLAT"].strip(), r["INTPTLONG"].strip()])
        n += 1
print(f"wrote {n} ZCTAs to {OUT}")
