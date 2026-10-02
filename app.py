"""LeaseLens — Streamlit app.  Run:  streamlit run app.py"""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from leaselens import budget as bud
from leaselens import data, lease_scan, llm, ui

ROOT = Path(__file__).resolve().parent
SAMPLE_LEASE = (ROOT / "data" / "sample_lease.txt").read_text(encoding="utf-8")

SOURCE_SHORT = {"snowflake": "❄️ Snowflake · Census ACS", "snowflake-snapshot": "❄️ Census ACS (Snowflake snapshot)"}
SOURCE_LONG = {"snowflake": "Snowflake, live (Census ACS)",
               "snowflake-snapshot": "Snowflake snapshot (data/area_stats_snowflake.csv)"}

st.set_page_config(page_title="LeaseLens", page_icon="🏠", layout="wide", initial_sidebar_state="expanded")
ui.inject_css()
ui.reset_cards()

ss = st.session_state
for k, v in {"page": "landing", "user": None, "zip": "85281", "rent": 1950, "bedrooms": 2,
             "job": 1200, "aid": 500, "parents": 300, "other_exp": 585, "people": 2,
             "utilities": 150, "fees": 0, "deposit": 1950, "reports": [], "lease_text": ""}.items():
    ss.setdefault(k, v)
# Streamlit drops a widget's state when its page isn't shown; re-assigning keeps
# shared inputs (rent, bedrooms, budget fields) alive across screens.
for k in ("zip", "rent", "bedrooms", "job", "aid", "parents", "other_exp", "people", "utilities", "fees",
          "deposit", "lease_text"):
    ss[k] = ss[k]


def go(page: str) -> None:
    ss.page = page


@st.cache_data(ttl=60, show_spinner=False)
def model_ok() -> bool:
    return llm.is_available()


def save_report(kind: str, summary: str, payload: dict) -> None:
    ss.reports.insert(0, {"kind": kind, "summary": summary, "when": datetime.now().strftime("%b %d, %I:%M %p"),
                          "data": payload})
    st.toast("Saved to your reports ✅")


# =====================================================================
# Public pages: landing + login
# =====================================================================
def landing() -> None:
    hero, art = st.columns([6, 5], gap="large")
    with hero:
        st.markdown(ui.logo(40, "2rem"), unsafe_allow_html=True)
        st.markdown('<h1 style="font-size:2.4rem;line-height:1.15;margin:.6rem 0 .4rem">Know if your first apartment '
                    'is a good deal <span style="color:#4F46E5">before you sign.</span></h1>'
                    '<p style="color:#6B7280;font-size:1.05rem">Get clear, data-backed answers in minutes so you can '
                    'rent with confidence.</p>', unsafe_allow_html=True)
        q1, q2, q3 = st.columns(3)
        for col, icon, text in ((q1, "📍", "Is the rent fair for the area?"), (q2, "🧮", "Can I afford it?"),
                                (q3, "📄", "What in the lease should I ask about?")):
            col.markdown(f'<div style="font-size:1.4rem">{icon}</div><div style="font-size:.85rem;font-weight:600">'
                         f'{text}</div>', unsafe_allow_html=True)
        st.write("")
        b1, b2 = st.columns([1, 2])
        b1.button("Get Started", type="primary", use_container_width=True, on_click=go, args=("login",))
        b2.markdown('<p style="color:#6B7280;font-size:.85rem;padding-top:.5rem">Free to use · Powered by Census '
                    'data · Open source</p>', unsafe_allow_html=True)
    with art:
        st.markdown(ui.hero_illustration(), unsafe_allow_html=True)

    st.write("")
    cols = st.columns(4, gap="medium")
    features = [
        ("📍", "1. Rent Check", "Compare your rent to the area.",
         ["Enter a zip code, rent, and bedrooms", "See how your rent compares to the area median",
          "Find nearby areas with lower typical rent", "Powered by Census ACS data"]),
        ("🧮", "2. Budget Check", "See if you can afford it.",
         ["Add your income sources and roommates", "Includes estimated utilities and deposit",
          "Shows what's left each month", "Flags if housing costs are over 30% of your income",
          "Get a plain-English summary"]),
        ("📄", "3. Lease Scan", "Find important clauses.",
         ["Paste or upload your lease", "Checks deposit, early termination, auto-renewal, fees, roommate liability…",
          "Shows exact quotes, explanations, and questions to ask", "Every quote is verified against your text",
          "Not legal advice"]),
    ]
    for col, (icon, title, sub, bullets) in zip(cols[:3], features):
        with ui.card(col):
            st.markdown(f'<div style="font-size:1.6rem">{icon}</div><p class="ll-h" style="font-size:1.05rem">{title}</p>'
                        f'<p class="ll-sub">{sub}</p><ul class="ll-feature">'
                        + "".join(f"<li>{b}</li>" for b in bullets) + "</ul>", unsafe_allow_html=True)
    with ui.card(cols[3]):
        st.markdown('<p class="ll-h" style="font-size:1.05rem">Built for students<br>by students</p><ul class="ll-feature" '
                    'style="list-style:none;padding-left:0">'
                    "<li>🏛️ Real data from the U.S. Census (ACS) via Snowflake</li>"
                    "<li>🧠 Open-weight AI (runs locally with Ollama)</li>"
                    "<li>⏱️ Simple, clear answers in about a minute</li>"
                    "<li>⬇️ Export your results</li>"
                    "<li>💜 MIT licensed and open source</li></ul>", unsafe_allow_html=True)


def login() -> None:
    art, form = st.columns([6, 5], gap="large")
    with art:
        st.markdown(ui.logo(40, "2rem"), unsafe_allow_html=True)
        st.markdown('<h2 style="margin:.5rem 0">Know if your first apartment is a good deal before you sign.</h2>',
                    unsafe_allow_html=True)
        st.markdown(ui.hero_illustration(), unsafe_allow_html=True)
    with form:
        st.write("")
        with ui.card():
            st.markdown('<p class="ll-h">Welcome back</p><p class="ll-sub">Log in to save your searches, budgets, '
                        'and lease checks.</p>', unsafe_allow_html=True)
            with st.form("login", border=False):
                email = st.text_input("Email address", placeholder="you@school.edu")
                st.text_input("Password", type="password")
                if st.form_submit_button("Log In", type="primary", use_container_width=True):
                    if "@" not in email:
                        st.error("Enter an email address.")
                    else:
                        ss.user = email.split("@")[0].title()
                        go("rent")
                        st.rerun()
            st.markdown('<p style="text-align:center;color:#9CA3AF;font-size:.8rem">— or continue with —</p>',
                        unsafe_allow_html=True)
            for provider in ("Google", "GitHub"):
                if st.button(f"Continue with {provider}", use_container_width=True):
                    ss.user = "Guest"
                    go("rent")
                    st.rerun()
            st.caption("Demo sign-in: accounts and saved reports live only in this browser session.")
        st.button("← Back", on_click=go, args=("landing",))


# =====================================================================
# App shell
# =====================================================================
NAV = [("rent", "📍  Rent Check"), ("budget", "🧮  Budget Check"), ("lease", "📄  Lease Scan"),
       ("saved", "🗂️  Saved Reports")]
NAV_BOTTOM = [("profile", "👤  Profile"), ("settings", "⚙️  Settings"), ("help", "❔  Help")]


def sidebar() -> None:
    with st.sidebar:
        st.markdown(ui.logo(), unsafe_allow_html=True)
        st.write("")
        for key, label in NAV:
            st.button(label, key=f"nav_{key}", use_container_width=True, on_click=go, args=(key,),
                      type="primary" if ss.page == key else "secondary")
        st.markdown("<div style='height:28vh'></div>", unsafe_allow_html=True)
        for key, label in NAV_BOTTOM:
            st.button(label, key=f"nav_{key}", use_container_width=True, on_click=go, args=(key,),
                      type="primary" if ss.page == key else "secondary")
        _, source = data.load_table()
        st.caption(f"{SOURCE_SHORT.get(source, '🧪 Mock data')} · "
                   f"{'🟢' if model_ok() else '🔴'} {llm.MODEL}")


# ---------------------------------------------------------------------
def page_rent() -> None:
    left, right = st.columns([5, 7], gap="large")
    with left:
        with ui.card():
            ui.header(1, "Rent Check", "See if the rent is fair for the area.")
            st.text_input("Zip code", key="zip", max_chars=5)
            a, b = st.columns(2)
            a.number_input("Monthly rent ($)", 200, 10000, step=25, key="rent")
            b.selectbox("Bedrooms", [0, 1, 2, 3, 4], key="bedrooms",
                        format_func=lambda n: "Studio" if n == 0 else f"{n} bedroom{'s' if n > 1 else ''}")
            st.caption("Median gross rent covers all unit sizes in the ZIP, and includes utilities "
                       "the tenant pays. Use it as a baseline.")

    stats = data.get_area_stats(ss.zip)
    with right:
        with ui.card():
            if not stats:
                st.warning("We don't have Census data for that ZIP yet. Try a nearby ZIP.")
                return
            pct = data.rent_vs_median(ss.rent, stats["median_rent"])
            color = ui.RED if pct > 5 else (ui.GREEN if pct < -5 else ui.AMBER)
            st.markdown(f'<div class="ll-big">Your rent is <span style="color:{color}">{abs(pct):.0f}%</span> '
                        f'{"above" if pct >= 0 else "below"} the median for this zip.</div>'
                        f'<p class="ll-sub">📅 Census baseline: {html.escape(stats["year"])}'
                        f' · {html.escape(stats["place"])}</p>', unsafe_allow_html=True)
            st.markdown(ui.gauge_svg(ss.rent, stats["median_rent"]), unsafe_allow_html=True)

        cheaper = [n for n in stats["nearby"] if n["median_rent"] < stats["median_rent"]][:5]
        with ui.card():
            st.markdown('<p class="ll-h" style="font-size:1rem">Nearby areas with lower typical rent</p>',
                        unsafe_allow_html=True)
            if not cheaper:
                st.caption("No cheaper ZIPs within 8 miles in our data.")
            rows = ""
            for n in cheaper:
                drop = (stats["median_rent"] - n["median_rent"]) / stats["median_rent"] * 100
                rows += (f'<div class="ll-row"><span>📍 <b>{n["zip"]}</b> <span style="color:#6B7280">'
                         f'({html.escape(n["place"])})</span></span><span style="color:#6B7280">{n["miles"]} mi</span>'
                         f'<b>${n["median_rent"]:,}</b>{ui.pill(f"~{drop:.0f}% lower", ui.GREEN, "#E8F6EF")}</div>')
            st.markdown(rows, unsafe_allow_html=True)
            if cheaper and stats["lat"] is not None:
                with st.expander("🗺️ View on map"):
                    pts = pd.DataFrame([{"lat": stats["lat"], "lon": stats["lon"], "c": "#E5484D", "s": 260}] +
                                       [{"lat": n["lat"], "lon": n["lon"], "c": "#4F46E5", "s": 180} for n in cheaper])
                    st.map(pts, latitude="lat", longitude="lon", color="c", size="s", height=260)
        if st.button("💾 Save this rent check"):
            save_report("Rent check", f"{ss.zip}: ${ss.rent:,} is {pct:+.0f}% vs median ${stats['median_rent']:,}",
                        {"rent": ss.rent, "bedrooms": ss.bedrooms, "area": stats})


# ---------------------------------------------------------------------
def page_budget() -> None:
    left, right = st.columns([5, 7], gap="large")
    with left:
        with ui.card():
            ui.header(2, "Budget Check", "See if you can afford it.")
            st.markdown("**Your monthly income**")
            st.number_input("Part-time job", 0, 20000, step=50, key="job")
            st.number_input("Financial aid", 0, 20000, step=50, key="aid")
            st.number_input("Parent/other support", 0, 20000, step=50, key="parents")
            st.number_input("Other monthly expenses (food, phone, transport)", 0, 20000, step=25, key="other_exp")
            st.markdown("**Housing details**")
            st.number_input("Monthly rent", 0, 20000, step=25, key="rent")
            st.number_input("Number of roommates (including you)", 1, 8, key="people")
            st.number_input("Estimated utilities (per month)", 0, 3000, step=10, key="utilities",
                            help="Whole unit. Ask the landlord for last year's average bill.")
            st.number_input("Monthly fees (amenity, trash, parking)", 0, 3000, step=5, key="fees")
            st.number_input("Security deposit (one-time)", 0, 20000, step=50, key="deposit",
                            help="Shown as part of your up-front cost, not your monthly budget.")

    income = ss.job + ss.aid + ss.parents
    res = bud.compute_budget(rent=ss.rent, bedrooms=ss.bedrooms, monthly_income=income, roommates=ss.people - 1,
                             utilities=ss.utilities, monthly_fees=ss.fees, deposit=ss.deposit,
                             other_expenses=ss.other_exp)
    with right:
        with ui.card():
            lc = ui.GREEN if res.left_over >= 0 else ui.RED
            st.markdown(f'<div class="ll-big">You\'d have about <span style="color:{lc}">${res.left_over:,.0f}/month'
                        f'</span> left after housing and expenses.</div>', unsafe_allow_html=True)
            st.markdown(ui.budget_bar(res.housing_total, res.other_expenses, res.left_over, income),
                        unsafe_allow_html=True)
            st.write("")
            st.markdown(f"Your housing costs are about **{res.housing_pct:.0f}%** of your income.")
            msg = {"ok": ("✅", "This is within the 30% guideline.", ui.GREEN),
                   "stretch": ("⚠️", "This is above the 30% guideline: money will be tight.", ui.AMBER),
                   "over": ("⛔", "This is well above the 30% guideline.", ui.RED)}[res.status]
            st.markdown(f'<p style="color:{msg[2]};font-weight:600">{msg[0]} {msg[1]}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="ll-sub">Cash needed up front (your deposit share + first month): '
                        f'<b>${res.upfront_cost:,.0f}</b></p>', unsafe_allow_html=True)

            key = json.dumps(res.to_dict(), sort_keys=True)
            summary = ss.get("ai_summary", {}).get(key) or bud.fallback_summary(res)
            st.markdown(f'<div class="ll-meaning"><b>💡 What this means</b><br>{html.escape(summary)}</div>',
                        unsafe_allow_html=True)
            st.write("")
            a, b = st.columns(2)
            if a.button("✨ Explain with local AI", use_container_width=True):
                try:
                    with st.spinner(f"Asking {llm.MODEL}…"):
                        text = llm.chat(
                            "You are a friendly money coach for a college student renting their first apartment. "
                            "In 3 short sentences, explain their monthly budget in plain English. Use only the "
                            "numbers given; all amounts are per month except upfront_cost. Mention the 30% "
                            "guideline. End with one practical tip. No legal or investment advice.",
                            key, temperature=0.3)
                    ss.setdefault("ai_summary", {})[key] = text.strip()
                    st.rerun()
                except llm.LLMUnavailable:
                    st.error("The local model isn't running, so you're seeing the template summary.")
            if b.button("💾 Save budget", use_container_width=True):
                save_report("Budget check", f"${res.left_over:,.0f}/mo left · housing {res.housing_pct:.0f}% of income",
                            res.to_dict())


# ---------------------------------------------------------------------
def read_upload(f) -> str:
    if f.name.lower().endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(f).pages)
    return f.read().decode("utf-8", errors="replace")


def highlighted(text: str, cards: list[dict]) -> str:
    out, pos = [], 0
    for c in sorted((c for c in cards if c["verified"]), key=lambda c: c["start"]):
        if c["start"] < pos:
            continue
        fg, bg, _ = ui.RISK[c["risk_level"]]
        out += [html.escape(text[pos:c["start"]]),
                f'<mark class="ll" style="background:{bg};border-bottom:2px solid {fg}" title="{c["label"]}">'
                f'{html.escape(text[c["start"]:c["end"]])}</mark>']
        pos = c["end"]
    out.append(html.escape(text[pos:]))
    return ('<div style="white-space:pre-wrap;font-size:.84rem;max-height:560px;overflow:auto;padding:14px;'
            'background:#fff;border:1px solid #E6E8F0;border-radius:12px">' + "".join(out) + "</div>")


def page_lease() -> None:
    with ui.card():
        h, up = st.columns([3, 2])
        with h:
            ui.header(3, "Lease Scan", "Paste your lease to find important clauses.")
        with up:
            st.file_uploader("Upload File", type=["txt", "pdf"], label_visibility="collapsed", key="upload",
                             on_change=lambda: ss.upload and ss.__setitem__("lease_text", read_upload(ss.upload)))
        st.text_area("Paste your lease text", key="lease_text", height=200, max_chars=60000,
                     placeholder="Paste your lease here…", label_visibility="collapsed")
        a, _, b = st.columns([1, 3, 1])
        a.button("Use sample lease", on_click=lambda: ss.__setitem__("lease_text", SAMPLE_LEASE))
        scan = b.button("Scan Lease", type="primary", use_container_width=True, disabled=not ss.lease_text.strip())

    if scan:
        try:
            with st.spinner(f"Reading your lease with {llm.MODEL}… (30–90 s on a laptop)"):
                ss.cards = lease_scan.scan_lease(ss.lease_text)
                ss.scanned_text = ss.lease_text
        except llm.LLMUnavailable as e:
            st.error(f"The local model isn't running. Start Ollama and try again. ({e})")
        except ValueError as e:
            st.error(f"The model's answer wasn't valid JSON. Try again. ({e})")

    cards = ss.get("cards")
    if not cards or ss.get("scanned_text") != ss.lease_text:
        return

    s = lease_scan.stats(cards)
    removed = f", {s['dropped']} unverifiable quote(s) removed" if s["dropped"] else ""
    st.markdown(f'<p class="ll-h" style="font-size:1.1rem;margin-top:.8rem">Scan Results</p>'
                f'<p class="ll-sub">Each clause is verified word-for-word against your text '
                f'({s["verified"]} verified{removed}). '
                f'This is not legal advice.</p>', unsafe_allow_html=True)
    tab_cards, tab_text = st.tabs(["Clauses", "Your lease, highlighted"])
    with tab_cards:
        order = {"high": 0, "medium": 1, "low": 2}
        for c in sorted(cards, key=lambda c: (not c["found"], order[c["risk_level"]])):
            icon = {"high": "🔴", "medium": "🟠", "low": "🟢"}[c["risk_level"]]
            label = f"{icon}  {c['label']}  ·  {ui.RISK[c['risk_level']][2]}" + ("" if c["found"] else "  ·  not in lease")
            with st.expander(label, expanded=c["found"] and c["risk_level"] == "high"):
                if c["quote"]:
                    st.markdown(f'<div class="ll-quote">“{html.escape(c["quote"])}”</div>', unsafe_allow_html=True)
                st.markdown(f"**Plain English**  \n{c['explanation']}")
                if c["question_to_ask"]:
                    st.markdown(f'<div class="ll-ask">❓ <b>Question to ask</b><br>{html.escape(c["question_to_ask"])}</div>',
                                unsafe_allow_html=True)
    with tab_text:
        st.markdown(highlighted(ss.scanned_text, cards), unsafe_allow_html=True)
    a, b = st.columns(2)
    a.download_button("⬇️ Download results (JSON)", lease_scan.to_json(cards), "lease_check.json",
                      mime="application/json", use_container_width=True)
    if b.button("💾 Save lease scan", use_container_width=True):
        save_report("Lease scan", f"{s['high']} high-risk clause(s), {s['verified']} verified quotes",
                    json.loads(lease_scan.to_json(cards)))


# ---------------------------------------------------------------------
def page_saved() -> None:
    st.markdown('<p class="ll-h">Saved Reports</p><p class="ll-sub">Saved for this session. Download anything you '
                'want to keep.</p>', unsafe_allow_html=True)
    if not ss.reports:
        st.info("Nothing saved yet. Use the 💾 buttons on each screen.")
    for i, r in enumerate(ss.reports):
        with ui.card():
            a, b = st.columns([4, 1])
            a.markdown(f"**{r['kind']}** · {r['summary']}  \n<span class='ll-sub'>{r['when']}</span>",
                       unsafe_allow_html=True)
            b.download_button("Download", json.dumps(r, indent=2, default=str),
                              f"leaselens_{r['kind'].replace(' ', '_').lower()}_{i}.json", key=f"dl{i}")


def page_profile() -> None:
    st.markdown(f'<p class="ll-h">Profile</p><p class="ll-sub">Signed in as {html.escape(ss.user or "Guest")} '
                '(demo session).</p>', unsafe_allow_html=True)
    if st.button("Log out"):
        ss.user = None
        go("landing")
        st.rerun()


def page_settings() -> None:
    st.markdown('<p class="ll-h">Settings</p>', unsafe_allow_html=True)
    _, source = data.load_table()
    with ui.card():
        st.markdown(f"**Data source:** {SOURCE_LONG.get(source, 'Mock data: add .streamlit/secrets.toml to use Snowflake')}")
        st.markdown(f"**Model:** `{llm.MODEL}` at `{llm.URL}` — {'online 🟢' if model_ok() else 'offline 🔴'}")
        st.caption("Change the model with the LEASELENS_MODEL environment variable (e.g. qwen2.5:3b on slower laptops).")


def page_help() -> None:
    st.markdown('<p class="ll-h">Help</p>', unsafe_allow_html=True)
    with ui.card():
        st.markdown("""
**How the numbers work.** Rent is compared with the Census American Community Survey median gross rent for your
ZIP. ACS figures are multi-year estimates, so they lag the current market: treat them as a baseline.

**The 30% guideline.** Spending more than about 30% of income on housing is commonly considered a stretch.

**Lease scan.** An open-weight model running on your machine reads the lease. Every quote it returns is checked
word-for-word against your text; anything that doesn't match is removed.

**Not legal advice.** For high-risk clauses, talk to your campus legal clinic or a local tenant union.
""")


# =====================================================================
if ss.user is None:
    {"landing": landing, "login": login}.get(ss.page, landing)()
else:
    if ss.page in ("landing", "login"):
        ss.page = "rent"
    sidebar()
    {"rent": page_rent, "budget": page_budget, "lease": page_lease, "saved": page_saved,
     "profile": page_profile, "settings": page_settings, "help": page_help}[ss.page]()
