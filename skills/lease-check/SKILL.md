---
name: lease-check
description: Reviews residential lease text for a first-time renter and flags eight clause types (security deposit, early termination, auto-renewal, utilities, extra fees, roommate liability, subletting, maintenance). Returns structured JSON cards with a verbatim quote, a plain-English explanation, a risk level and a question to ask the landlord. Use when someone pastes an apartment lease or rental agreement, asks what to watch out for before signing, or asks whether a lease clause is normal.
license: MIT
metadata:
  author: leaselens
  version: "1.0"
---

# Lease Check

Help a first-time renter (usually 18–22, no rental history) understand a lease **before** they sign it. You are explaining, not giving legal advice.

## Inputs

- The full lease text (plain text; if given a PDF or image, extract the text first).

## Steps

1. Read the clause checklist in [references/CLAUSES.md](references/CLAUSES.md). It lists the eight `clause_type` ids, what each one covers, and what makes it low, medium or high risk.
2. For **each** of the eight clause types, search the lease for the passage that governs it.
3. Fill one object per clause type using the format in [assets/output_schema.json](assets/output_schema.json). A filled example is in [assets/example_output.json](assets/example_output.json).
   - `quote` must be copied **character-for-character** from the lease: one contiguous passage, no paraphrasing, no ellipses, no added words. Keep it under ~60 words; pick the sentence that matters most.
   - If the lease does not address a clause type, set `found: false`, `quote: ""`, and use `explanation` to say what is missing and why that matters.
   - `explanation`: 1–2 sentences, plain English, written for a 19-year-old. Say what it means for *their money or their options*.
   - `risk_level`: `low`, `medium`, or `high`, using the guidance in CLAUSES.md.
   - `question_to_ask`: one specific, polite question the renter can ask the landlord on the tour.
4. Verify every quote against the original lease text with `python scripts/verify_quotes.py lease.txt result.json`. Drop (or set `found: false` on) any card whose quote does not appear in the lease. Never show an unverified quote to the user.
5. Return only the JSON object: `{"clauses": [ ...8 objects... ]}`.

## Rules

- Never invent clauses. If you are unsure a passage covers a clause type, prefer `found: false`.
- Do not state what local law requires; laws vary by state and city. Suggest checking with a campus legal clinic or tenant union for anything marked `high`.
- Always remind the user: *This is not legal advice.*

## Edge cases

- **One passage covers two types** (e.g., "Tenant pays all utilities and a $25 trash fee"): quote the same passage in both cards.
- **Very long lease**: scan section headings first, then read the relevant sections closely.
- **Addenda** (pet, parking, community policies) count as part of the lease; fees hidden there are common.
