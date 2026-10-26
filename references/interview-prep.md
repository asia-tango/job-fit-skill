# Interview prep (Prep mode)

Used when the user is invited to an interview for one vacancy. Output: Markdown, rendered with
`scripts/build_page.py`, quotes checked with `scripts/verify_quotes.py`. It builds on the CV and the vacancy only.

## Rules

- Never write the answers for the user. Give the **frame**: which CV episode fits, what to say first, what to avoid.
  The words are the user's.
- Every episode comes from the CV or from something the user confirmed in chat (`confirmed by you`).
  If the CV line has no detail (scope, result, role), ask a multiple-choice question first (`intake.md`), max 3.
- "We" stays "we". Never turn a team result into a personal one.
- Claims about the company, the interviewer or the process are `guess` unless the vacancy states them.
- A weak spot (❌ gap, ❓ not in CV) gets an honest line: what the user has, what they don't, how they'd close it.
  No bluffing advice.
- If the vacancy or invitation forbids AI help in the process, say so and stop at the checklist of topics.

If the user asks for "weak spots only", give only sections 2 (the ❌ and ❓ questions) and 3.

## Sections, in this order

1. **Process and format** – only what is stated (stages, length, who). Unknown parts listed as "ask".
2. **Likely questions** – 8–12, grouped (role, technical, behavioral, motivation). Each has:
   - the requirement it comes from, quoted from the vacancy;
   - the CV episode that answers it, quoted from the CV (or `confirmed by you`);
   - a one-line frame: what to open with, what number or scope to mention if the CV has it.
   Put the questions about ❌ and ❓ rows first: those are where the interviewer will push.
3. **Weak spots** – each gap or unknown with an honest answer frame and what to say you are doing about it.
4. **Brush up** – technical topics taken from the vacancy's requirements, ordered by how central they are.
   Topics only, no tutorials.
5. **Money and format** – how to answer "what are your expectations", using the profile's minimum and basis.
   Ask the user's range if the profile has none. Say when to ask about contract type.
6. **Your questions for them** – 4–6 from `questions-bank.md`, chosen for this vacancy, each with the reason.
7. **Before the call** – a short checklist (CV open, the two or three episodes ready, questions printed,
   time zone and link checked).

## Style

Direct, no pep talk. Short lines. Marks (✅ ⚠️ ❓ ❌) in front of the likely questions show how well the CV covers them.
