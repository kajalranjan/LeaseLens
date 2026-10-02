# 🏠 LeaseLens

**Know if your first apartment is a good deal before you sign.**

A student enters a ZIP code, the rent, and their income. In about a minute they learn:

1. **Rent check:** is the rent fair for that area? (Census ACS median gross rent, plus cheaper ZIPs nearby)
2. **Budget check:** can they afford it? (rent split, utilities, fees, deposit, the 30% guideline, plain-English summary from an open model)
3. **Lease scan:** what in the lease should they ask about? (8 clause types, exact quotes, questions for the landlord)

> **Every flag is verified word-for-word against your lease.** After the model answers, code checks that each quote really appears in the lease text; anything that doesn't is removed.

*LeaseLens is educational. It is not legal or financial advice.*

## How it's built

```
Streamlit app (app.py)
 ├─ Rent + budget  → Snowflake (Census ACS from a free Marketplace listing, explored with CoCo)
 │                   leaselens/data.py · sql/02_area_stats.sql
 ├─ Lease scan     → open-weight model via Ollama (Qwen 2.5 7B / Llama 3.1 8B)
 │                   leaselens/lease_scan.py · leaselens/llm.py
 └─ Agent Skill    → skills/lease-check/  (Agent Skills open standard)
```

The app builds its prompt from the skill folder (`CLAUSES.md`, `example_output.json`) and reuses the skill's `verify_quotes.py`, so the published skill and the app never drift apart.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# open-weight model (https://ollama.com)
ollama pull qwen2.5:7b          # slow laptop? qwen2.5:3b and set LEASELENS_MODEL=qwen2.5:3b
ollama serve                    # if it isn't already running

streamlit run app.py
```

Without Snowflake credentials the app runs on `data/mock_area_stats.csv` (clearly labeled MOCK). See **[docs/SNOWFLAKE_SETUP.md](docs/SNOWFLAKE_SETUP.md)** to connect real Census data.

Hosted open model instead of Ollama (vLLM, LM Studio, Together, etc.):
```bash
export LEASELENS_LLM_API=openai LEASELENS_LLM_URL=https://... LEASELENS_LLM_KEY=... LEASELENS_MODEL=...
```

Tests: `pytest -q`

## Who needs a powerful computer?

Only the machine **running the app**. Visitors use LeaseLens in their browser, so their phone or laptop doesn't matter.

| Where it runs | Model setup |
|---|---|
| Demo laptop (16 GB+ RAM) | Ollama + `qwen2.5:7b` (default) |
| Dev laptop with 8 GB RAM | Ollama + `qwen2.5:3b` (`LEASELENS_MODEL=qwen2.5:3b`), or point `LEASELENS_LLM_URL` at a teammate's machine |
| Public website (Streamlit Community Cloud etc.) | A hosted open-weight model through an OpenAI-compatible API (see above). Free hosting can't run Ollama itself. |

## The Agent Skill

`skills/lease-check/` follows the [Agent Skills specification](https://agentskills.io/specification):

```
skills/lease-check/
├── SKILL.md                    # name, description, license + instructions
├── references/CLAUSES.md       # the 8 clause types and risk rules
├── assets/output_schema.json   # JSON Schema for the result
├── assets/example_output.json
└── scripts/verify_quotes.py    # word-for-word quote check (stdlib only)
```

Drop the folder into any agent that supports skills. Validate with `skills-ref validate skills/lease-check`.

## Data notes

ACS figures are multi-year estimates, so they lag today's market. The app always shows the estimate year and frames results as "compared to the area baseline." Median gross rent includes tenant-paid utilities and covers all unit sizes.

Sources: rent and income come from the **Snowflake Public Data (Free)** listing (`SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE`, ACS variables `B25064_001E_5YR` and `B19013_001E_5YR_<year>`), explored and queried with CoCo. `data/area_stats_snowflake.csv` is a snapshot of that query for the Phoenix metro (850/852/853 ZIPs), so the demo works offline. ZIP coordinates and display city names come from the open-source [`zipcodes`](https://pypi.org/project/zipcodes/) package (MIT).

## Team split

- **Person A (data):** Snowflake, CoCo exploration, `sql/`, `leaselens/data.py`, `leaselens/budget.py`
- **Person B (AI + UI):** Ollama, `leaselens/lease_scan.py`, `leaselens/llm.py`, `app.py`, `leaselens/ui.py`, `skills/`

Shared contracts:
```python
get_area_stats(zip) -> {median_rent, median_income, year, place, source, nearby: [...]}
scan_lease(text)    -> [clause cards]
```

## License

MIT, see [LICENSE](LICENSE).
