# Report JSON schema

The analysis is written as JSON, then `scripts/build_report.py` renders it as one styled HTML page.
Write the JSON directly; do not write the analysis twice (once in chat, once in JSON).

```json
{
  "profile_source": "attached profile",
  "title": "optional, defaults to the vacancy title",
  "summary": {
    "rows": [{"vacancy": "...", "verdict": "apply|questions|check|skip", "reason": "...", "check": "..."}],
    "patterns": ["..."],
    "next": ["..."]
  },
  "vacancies": [{
    "title": "Role, Company",
    "verdict": {"mark": "apply|questions|check|skip", "text": "one or two sentences"},
    "would_change": ["if X is confirmed, apply"],
    "requirements": [{
      "requirement": "verbatim from the vacancy",
      "evidence": "verbatim from the CV (omit if none)",
      "status": "match|partial|unknown|gap",
      "note": "optional",
      "confirmed": false
    }],
    "cv_fixes": [{"kind": "Move up|Reword|Add (only if confirmed)|Remove", "text": "..."}],
    "growth": {
      "new": [{"text": "...", "tag": "stated|guess"}],
      "same": [{"text": "...", "tag": "stated|guess"}],
      "unknown": [{"text": "...", "tag": "guess"}]
    },
    "red_flags": [{"quote": "verbatim from the vacancy", "text": "why it matters"}],
    "money": "stated or not stated; gross/net, contract, format, location",
    "questions": [{"group": "Role", "question": "...", "why": "..."}],
    "talking_points": [{"point": "...", "cv": "verbatim", "vacancy": "verbatim", "confirmed": false}],
    "letter_draft": "optional; only when the user asked for an application text. Plain text, line breaks kept."
  }],
  "next_steps": [{"label": "Prepare for the interview", "command": "I got an invite for this vacancy. Prepare me."}],
  "decide": [{"question": "...", "options": ["a", "b"], "affects": "which verdict it can change"}]
}
```

## Rules

- `requirement`, `evidence`, red-flag `quote`, talking-point `cv` and `vacancy` are quotes, each from its own document:
  `evidence` and talking-point `cv` from the CV (`--cv`); `requirement`, red-flag `quote` and talking-point `vacancy`
  from the vacancy (`--vacancy`). The script refuses to render if a quote is not in its document, so a vacancy line
  pasted as CV evidence fails.
- `confirmed: true` means the user confirmed it in chat. Then `evidence` / `cv` is free text, is shown with a
  `confirmed by you` tag, and is not quote-checked. A `match` must still have evidence.
- `status` is ✅ `match`, ⚠️ `partial`, ❓ `unknown` (not in the CV, ask), ❌ `gap`. Marks are added by the script.
- Growth items need `stated` or `guess`.
- `next_steps` render as copy buttons under "What next". Always include two or three.
- Everything is HTML-escaped. Do not put HTML in any field.
- `letter_draft` renders as "Application draft" with a "check every claim" note and a copy button. Not quote-checked, so every claim in it must come from the CV, the profile or something the user confirmed.
- Omit sections that are empty. Single mode has no `summary`; batch mode has one.
