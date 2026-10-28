# Prep JSON schema

Interview prep (Prep mode, `interview-prep.md`) is written as JSON, then `scripts/build_prep.py` renders it as one
styled page, the same look as the report:

`python scripts/build_prep.py prep.json prep.html --cv <cv.txt> --vacancy <vacancy.txt>`

```json
{
  "lang": "optional: en (default) or uk – the language of headings and labels",
  "profile_source": "attached profile",
  "title": "Interview prep: <role, company> (optional, defaults to \"Interview prep\")",
  "process": "free text: only what is stated (stages, length, who); unknown parts as \"ask\"",
  "questions": [{
    "group": "role|technical|behavioral|motivation",
    "requirement": "verbatim from the vacancy",
    "status": "match|partial|unknown|gap",
    "episode": "verbatim from the CV (omit if none)",
    "confirmed": false,
    "frame": "free text, how to answer"
  }],
  "weak_spots": [{"text": "free text", "requirement": "verbatim from the vacancy (optional)"}],
  "brush_up": [{"topic": "free text", "vacancy": "verbatim from the vacancy (optional)"}],
  "money": "free text",
  "ask_them": [{"question": "free text", "why": "free text"}],
  "before_call": ["free text"],
  "next_steps": [{"label": "...", "command": "..."}]
}
```

## Rules

- Evidence lives only in quote fields, each checked against its own document: `requirement` (questions and
  weak spots) and brush-up `vacancy` against the vacancy; `episode` against the CV, at least 12 characters.
  A quote must not start or end in the middle of a word and may not join two files.
  The script refuses to write the page if a quote is not in its document. Fix the quote, don't use `--force`.
- `confirmed` is a boolean (`true` / `false`, never a string). `confirmed: true` means the user confirmed the
  episode in chat: then `episode` is free text, is not quote-checked, and is shown with a `confirmed by you` tag.
- `status` is ✅ `match`, ⚠️ `partial`, ❓ `unknown` (not in the CV, ask), ❌ `gap`. A `match` needs an `episode`.
  Put the ❌ and ❓ questions first. `group` is one of the four groups; questions are shown grouped.
- Every section is optional and no field is required. When the vacancy forbids AI help, a prep with only
  `brush_up` (the topic checklist) is valid.
- Everything else is free text, and free text is a string (or null); a number, list or object is an error (exit 1).
  It is shown without quote marks, so it never looks like a citation (same rule as `report-schema.md`).
  `next_steps` keep their quote marks: they are phrases to paste, not claims.
- A quote field that is present (not null) must be non-blank text.
- Inputs: both `--cv` and `--vacancy` are required, or no page is written (there is no `--source`). An empty file
  (only whitespace, e.g. a scanned PDF), or the same file (or the same text) given as both the CV and the vacancy,
  is refused with exit 2. A file under 200 characters without spaces only prints a warning.
- `next_steps` render as copy buttons under "What next". Include two or three.
