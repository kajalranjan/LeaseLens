"""Visual building blocks for the Streamlit UI (CSS + small HTML components)."""
from __future__ import annotations

import html
import math

import streamlit as st

INDIGO = "#4F46E5"
GREEN = "#22A06B"
RED = "#E5484D"
AMBER = "#F5A524"
MUTED = "#6B7280"
RISK = {"high": (RED, "#FDECEC", "High"), "medium": (AMBER, "#FEF6E7", "Medium"), "low": (GREEN, "#E8F6EF", "Low")}

LOGO_SVG = f"""<svg width="{{s}}" height="{{s}}" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M4 15 16 5l12 10" stroke="{INDIGO}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M8 13v13h16V13" stroke="{INDIGO}" stroke-width="3" stroke-linejoin="round"/>
<rect x="13" y="17" width="6" height="9" rx="1" fill="{INDIGO}"/></svg>"""

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown, .stButton button, input, textarea, label {{ font-family: 'Inter', sans-serif !important; }}
#MainMenu, footer, header [data-testid="stToolbar"] {{ visibility: hidden; }}
.block-container {{ padding-top: 1.6rem; max-width: 1180px; }}

/* sidebar */
section[data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid #E6E8F0; }}
section[data-testid="stSidebar"] .stButton button > div {{ justify-content: flex-start; width: 100%; }}
section[data-testid="stSidebar"] .stButton button {{
  justify-content: flex-start; border: none; background: transparent; color: #374151;
  font-weight: 500; padding: .45rem .75rem; border-radius: 10px; box-shadow: none; }}
section[data-testid="stSidebar"] .stButton button:hover {{ background: #F1F2FB; color: {INDIGO}; }}
section[data-testid="stSidebar"] .stButton button[kind="primary"] {{ background: #EEF0FF; color: {INDIGO}; font-weight: 600; }}

/* cards */
[class*="st-key-llcard"] {{ background: #FFFFFF; border-radius: 16px !important; box-shadow: 0 1px 2px rgba(16,24,40,.04); }}
[class*="st-key-llcard"] input, [class*="st-key-llcard"] textarea,
[class*="st-key-llcard"] [data-baseweb="select"] > div {{ background: #F6F7FB !important; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ background: #FFFFFF; border-radius: 16px !important;
  border-color: #E6E8F0 !important; box-shadow: 0 1px 2px rgba(16,24,40,.04); }}
.stButton button[kind="primary"], .stFormSubmitButton button {{ border-radius: 10px; font-weight: 600; }}
.stButton button {{ border-radius: 10px; }}
div[data-testid="stExpander"] details {{ border-radius: 12px; border-color: #E6E8F0; background: #fff; }}

/* text helpers */
.ll-h {{ font-size: 1.35rem; font-weight: 700; margin: 0; color: #1F2340; }}
.ll-sub {{ color: {MUTED}; font-size: .9rem; margin: .1rem 0 .8rem; }}
.ll-num {{ display:inline-flex; width:28px; height:28px; border-radius:50%; align-items:center; justify-content:center;
  background:#EEF0FF; color:{INDIGO}; font-weight:700; font-size:.85rem; margin-right:.5rem; }}
.ll-pill {{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:.75rem; font-weight:600; }}
.ll-big {{ font-size: 1.55rem; font-weight: 800; line-height: 1.25; color:#1F2340; }}
.ll-row {{ display:flex; align-items:center; justify-content:space-between; padding:.6rem 0; border-bottom:1px solid #F0F1F5; font-size:.9rem; }}
.ll-row:last-child {{ border-bottom:none; }}
.ll-quote {{ background:#F7F7FB; border-left:3px solid {INDIGO}; padding:.65rem .8rem; border-radius:8px; font-size:.88rem; color:#374151; }}
.ll-ask {{ background:#EEF0FF; border-radius:10px; padding:.65rem .8rem; font-size:.88rem; }}
.ll-hero {{ background: linear-gradient(135deg,#EEF0FF 0%,#F8F5FF 55%,#FFF7EE 100%); border-radius: 20px; padding: 2.2rem; }}
.ll-feature li {{ margin: .3rem 0; font-size: .9rem; color:#374151; }}
.ll-meaning {{ background:#F4F5FF; border-radius:12px; padding:.9rem 1rem; font-size:.9rem; color:#374151; }}
mark.ll {{ padding: 0 2px; border-radius: 3px; }}
</style>
"""


_card_n = [0]


def reset_cards() -> None:
    _card_n[0] = 0


def card(parent=None):
    """Bordered white card. Keys are numbered per run so CSS can target them."""
    _card_n[0] += 1
    return (parent or st).container(border=True, key=f"llcard{_card_n[0]}")


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def logo(size: int = 28, text_size: str = "1.3rem") -> str:
    return (f'<div style="display:flex;align-items:center;gap:.5rem">{LOGO_SVG.format(s=size)}'
            f'<span style="font-weight:800;font-size:{text_size};color:#1F2340">LeaseLens</span></div>')


def header(num: int, title: str, sub: str) -> None:
    st.markdown(f'<p class="ll-h"><span class="ll-num">{num}</span>{html.escape(title)}</p>'
                f'<p class="ll-sub">{html.escape(sub)}</p>', unsafe_allow_html=True)


def pill(text: str, fg: str, bg: str) -> str:
    return f'<span class="ll-pill" style="color:{fg};background:{bg}">{html.escape(text)}</span>'


def risk_pill(level: str) -> str:
    fg, bg, label = RISK.get(level, RISK["medium"])
    return pill(label, fg, bg)


def gauge_svg(rent: float, median: float) -> str:
    """Semicircle gauge: green (cheap) -> red (expensive), needle at your rent."""
    ratio = max(0.6, min(1.4, rent / median))
    t = (ratio - 0.6) / 0.8                     # 0 (left) .. 1 (right)
    ang = math.pi * (1 - t)
    cx, cy, r = 150, 140, 105
    nx, ny = cx + (r - 18) * math.cos(ang), cy - (r - 18) * math.sin(ang)
    pct = (rent - median) / median * 100
    col = RED if pct > 5 else (GREEN if pct < -5 else AMBER)
    word = "above median" if pct >= 0 else "below median"
    return f"""
<svg viewBox="0 0 300 200" width="100%" style="max-width:340px;display:block;margin:auto">
  <defs><linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="{GREEN}"/>
  <stop offset=".5" stop-color="#E8E1C8"/><stop offset="1" stop-color="{RED}"/></linearGradient></defs>
  <path d="M45 140 A105 105 0 0 1 255 140" fill="none" stroke="url(#g)" stroke-width="26" stroke-linecap="round"/>
  <line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#1F2340" stroke-width="4" stroke-linecap="round"/>
  <circle cx="{cx}" cy="{cy}" r="7" fill="#1F2340"/>
  <text x="45" y="178" text-anchor="middle" font-size="15" font-weight="700" fill="#1F2340">${median:,.0f}</text>
  <text x="45" y="194" text-anchor="middle" font-size="10" fill="{MUTED}">Median rent</text>
  <text x="150" y="178" text-anchor="middle" font-size="16" font-weight="800" fill="{col}">{abs(pct):.0f}%</text>
  <text x="150" y="194" text-anchor="middle" font-size="10" fill="{col}">{word}</text>
  <text x="255" y="178" text-anchor="middle" font-size="15" font-weight="700" fill="#1F2340">${rent:,.0f}</text>
  <text x="255" y="194" text-anchor="middle" font-size="10" fill="{MUTED}">Your rent</text>
</svg>"""


def budget_bar(housing: float, other: float, left: float, income: float) -> str:
    income = max(income, 1)
    parts = [("Housing", housing, INDIGO), ("Other expenses", other, "#B9BCF5"),
             ("Left over", max(left, 0), GREEN)]
    segs = "".join(f'<div style="width:{max(v, 0) / income * 100:.1f}%;background:{c}"></div>' for _, v, c in parts)
    labels = "".join(
        f'<div style="flex:1;font-size:.78rem;color:{MUTED}">{n}{f" ({v / income * 100:.0f}%)" if n == "Housing" else ""}'
        f'<br><b style="color:{c if n == "Left over" else "#1F2340"};font-size:.95rem">${v:,.0f}</b></div>'
        for n, v, c in parts)
    return (f'<div style="display:flex;height:14px;border-radius:999px;overflow:hidden;background:#EEF0F4;margin:.6rem 0">'
            f'{segs}</div><div style="display:flex;gap:.5rem">{labels}</div>')


def hero_illustration() -> str:
    """Simple apartment-building illustration so we don't depend on stock photos."""
    wins = "".join(f'<rect x="{x}" y="{y}" width="22" height="26" rx="3" fill="{"#FFE7B3" if (x + y) % 3 else "#DCE0FF"}"/>'
                   for x in (70, 110, 150, 190) for y in (70, 115, 160))
    return f"""<svg viewBox="0 0 300 260" width="100%" style="max-width:420px">
<rect x="0" y="0" width="300" height="260" rx="22" fill="#EEF0FF"/>
<circle cx="245" cy="55" r="26" fill="#FFD48A"/>
<rect x="50" y="45" width="180" height="200" rx="8" fill="#FFFFFF" stroke="#C9CDF8" stroke-width="2"/>
<rect x="50" y="45" width="180" height="16" rx="6" fill="{INDIGO}"/>
{wins}<rect x="125" y="205" width="30" height="40" rx="4" fill="{INDIGO}"/>
<rect x="18" y="200" width="22" height="45" rx="11" fill="#9BD3B5"/><rect x="240" y="190" width="26" height="55" rx="13" fill="#9BD3B5"/>
</svg>"""
