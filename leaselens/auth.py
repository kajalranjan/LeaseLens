"""Optional Supabase accounts: email/password sign-up + login, and saved reports per user.

Turned on only when SUPABASE_URL and SUPABASE_KEY are set (Streamlit secrets or env vars).
Without them the app keeps its demo login, so a Supabase problem can never break the site.
Uses Supabase's REST endpoints directly (no extra dependency).

Table (run once in Supabase SQL editor; see docs/SUPABASE_SETUP.md):
  reports(id, user_id uuid default auth.uid(), kind text, summary text, data jsonb, created_at)
  with row-level security so each user only sees their own rows.
"""
from __future__ import annotations

import os

import requests

TIMEOUT = 15


class AuthError(RuntimeError):
    pass


def _setting(name: str) -> str:
    try:
        import streamlit as st
        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return os.getenv(name, "").strip()


def enabled() -> bool:
    return bool(_setting("SUPABASE_URL") and _setting("SUPABASE_KEY"))


def _url(path: str) -> str:
    return _setting("SUPABASE_URL").rstrip("/") + path


def _headers(token: str | None = None) -> dict:
    key = _setting("SUPABASE_KEY")
    return {"apikey": key, "Authorization": f"Bearer {token or key}", "Content-Type": "application/json"}


def _error(r: requests.Response) -> str:
    try:
        j = r.json()
        return j.get("msg") or j.get("error_description") or j.get("message") or j.get("error") or r.text
    except ValueError:
        return r.text or f"HTTP {r.status_code}"


def _post(path: str, body: dict, token: str | None = None, extra: dict | None = None) -> requests.Response:
    try:
        return requests.post(_url(path), json=body, headers={**_headers(token), **(extra or {})}, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise AuthError("Couldn't reach the account service. Try again in a moment.") from e


def _session(j: dict) -> dict:
    user = j.get("user") or {}
    return {"token": j["access_token"], "user_id": user.get("id"), "email": user.get("email", "")}


def sign_up(email: str, password: str) -> dict | None:
    """Returns a session, or None if Supabase wants the user to confirm their email first."""
    r = _post("/auth/v1/signup", {"email": email, "password": password})
    if not r.ok:
        raise AuthError(_error(r))
    j = r.json()
    return _session(j) if j.get("access_token") else None


def sign_in(email: str, password: str) -> dict:
    r = _post("/auth/v1/token?grant_type=password", {"email": email, "password": password})
    if not r.ok:
        msg = _error(r)
        if "confirm" in msg.lower():
            msg = "Please confirm your email first (check your inbox), then log in."
        elif "invalid" in msg.lower():
            msg = "Wrong email or password."
        raise AuthError(msg)
    return _session(r.json())


def add_report(token: str, kind: str, summary: str, data: dict) -> None:
    r = _post("/rest/v1/reports", {"kind": kind, "summary": summary, "data": data}, token,
              {"Prefer": "return=minimal"})
    if not r.ok:
        raise AuthError(f"Couldn't save the report: {_error(r)}")


def list_reports(token: str) -> list[dict]:
    try:
        r = requests.get(_url("/rest/v1/reports"), headers=_headers(token), timeout=TIMEOUT,
                         params={"select": "kind,summary,data,created_at", "order": "created_at.desc"})
    except requests.RequestException as e:
        raise AuthError("Couldn't reach the account service.") from e
    if not r.ok:
        raise AuthError(f"Couldn't load your reports: {_error(r)}")
    return r.json()
