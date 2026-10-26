# CV check

## Evidence table

For each Must and each important Nice requirement in the vacancy, one row:

| Requirement (quote) | Evidence in CV (quote) | Status |
|---|---|---|

Rules:
- Both quotes are copied verbatim. They must pass `scripts/verify_quotes.py`.
- Short quotes are better than long ones (a phrase, not a paragraph).
- Don't count the same CV line as proof for unrelated requirements.
- If there is no evidence, write `—` in the evidence column.

Statuses. Always write the mark first:
- ✅ `match` – the CV shows it clearly.
- ⚠️ `partial` – the CV shows something close or an older or smaller version of it.
- ❓ `not in CV` – the CV is silent, but it may be true. Becomes a question.
- ❌ `gap` – the CV or the user's answers show they don't have it.

If the user confirmed it in the chat, keep the status but add `confirmed by you`: ✅ `match – confirmed by you`.

Years: compare the vacancy's years with the real dates in the CV. Do the arithmetic, don't eyeball.

## Fixes

Give concrete edits, not advice:

1. **Move up** – what is already in the CV but buried, and matters for this vacancy.
2. **Reword** – a line that undersells or is vague. Keep the facts. Don't upgrade the role ("owned" instead of "contributed" only if the CV or the user says so).
3. **Add, only if confirmed** – a skill or tool the vacancy needs. Ask first.
4. **Remove or shrink** – things that distract for this vacancy.

Each fix points to the CV line it changes.

## Honest limits

- Don't add keywords just to pass a filter. A keyword without a real story behind it fails at the interview.
- If the biggest gap can't be fixed by editing the CV, say so. Editing the CV doesn't create experience.
