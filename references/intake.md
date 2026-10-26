# Intake

## Question format (always)

Ask as multiple-choice, not as sentences to answer in prose.

1. If the session has a structured question tool (in Claude Code and Cowork it is `AskUserQuestion`), use it:
   - at most 4 questions per call, 2–4 options each, short labels;
   - the user can always type their own answer ("Other"), so don't add an "Other" option yourself;
   - several questions need several calls: group them (for example 4 + 4 + 3 for Setup);
   - put the recommended option first and mark it "(Recommended)" only when there is a real reason.
2. If there is no such tool, write the same questions as a numbered list with lettered options
   (`a) … b) … c) …`), so the user can answer with "1b, 2a, 3c". Nothing else needs to be typed.
3. For numbers (pay), give 2–3 bands that fit the CV's level and the market the user is in, plus "type your own".
   Never guess a number for the user.
4. Write options from the CV and the vacancy, not generic ones. A backend CV gets backend options.
5. Every question can be skipped. A skipped question stays empty in the profile; don't ask again.

## Follow-ups are quizzes too

There are no open-sentence questions, anywhere, including follow-ups like "what did the mentoring involve?" or "which pet projects?".
- Turn the question into options taken from the CV and the role. Several can apply: use multi-select.
  Example for mentoring: `code reviews` · `technical consultations` · `onboarding` · `architecture decisions with the team` · `formal mentor role`.
- The user's own words go in the same card: the question tool's "Other" field is that box, so don't ask a separate sentence.
  Without the tool, add a last option `z) other: type it`, answered like "1b,z: ...".
- Pet projects and links: options `none` · `the ones already in the CV` · `I'll type them`. After "I'll type them", take the reply as the answer.
- Put the follow-ups in the same call as the other questions when possible (max 4 per call), so the user answers one card, not a chat.
- Ready-made follow-up cards, so nothing is improvised (adapt the options to the CV, keep multi-select):

  | The user picked | Follow-up question | Options |
  |---|---|---|
  | Mentoring / leading people | What did it involve? | code reviews · technical consultations · onboarding · architecture decisions with the team · formal mentor role |
  | Mentoring (second card) | How many people, roughly? | 1–2 · 3–5 · more than 5 · varied |
  | Pet projects / portfolio | Which should go in the profile? | none · the ones already in the CV · I'll type them |
  | Tools or skills not in the CV | Which level? (one card per tool named in the answer) | used it in real work · small project only · learning now |
  | Certificates | Which kind? | cloud · language · domain / industry · course completion |
  | "Avoid: <domain>" | What exactly to flag? | the product itself · any work for such clients · only the core business |

  A follow-up card is sent as soon as the earlier answer is in. The next message after an answer is the next card, never a sentence.
- Before sending any message during Setup, check it: if it contains a question that is not inside the question tool
  (or lettered options), rewrite it as a card first.
- If you catch yourself writing "tell me…", "what did…", "which ones…" as a plain sentence, stop and rewrite it as options.

## Setup (once)

1. Read the CV. Decide the role family (`role-families.md`) and confirm it as the first question
   (options: the likely family, the second likely, "Other").
2. Core questions. Options are examples; adapt them to the CV.

   | # | Question | Options |
   |---|---|---|
   | 1 | Pay basis | gross per month · net per month · gross per year · net per year |
   | 2 | Minimum pay | 2–3 bands for the level and market · type your own |
   | 3 | Contract type | employee · contractor / sole proprietor · either |
   | 4 | Format | full-time · part-time · both |
   | 5 | Where can you work from | home country only · EU/UK time zone · US overlap OK · anywhere |
   | 6 | What do you want more of | scope and decisions · mentoring people · new domain · higher pay · stability |
   | 7 | What do you want to avoid | on-call · travel · outsourcing / staff augmentation · specific domains · specific tools |
   | 8 | Anything real that is missing from the CV | tools or skills · certificates · projects · nothing |

   Questions 6, 7 and 8 allow several answers.
   If the user picks "tools or skills" in 8, follow up with a multiple-choice question (see "Follow-ups are quizzes too"), never a free-text prompt.

3. Add 2–4 role-family questions from `role-families.md` (setup extras), in the same format.
4. Total at most 12. Don't ask what the CV already answers.

Then write the profile (below) and save it where the session allows.

## Saved profile

Chat apps run each conversation in a fresh sandbox, so a file saved in one chat is usually gone in the next.
Do not rely on the skill folder alone. At the end of Setup:

1. Fill in `profile.template.md` with the answers and confirmed extras, including its Keywords section
   (`stack` = tools and skills named in the CV, `avoid` = question 7).
2. Save it as `references/profile.local.md` if the folder is writable (Claude Code and similar).
3. Always also give the whole profile as `profile.md` (a file, or one block of text), render it as a page with `scripts/build_page.py` for reading, and tell the user, in two lines:
   keep it as `profile.md`, and attach it (or put it in a Project's files together with the CV) so the next chat doesn't repeat Setup.
4. The profile is private. Never commit it, never put it in a public repo.

At the start of any later session, look for the profile in this order: the skill folder, a file or block the user
attached or pasted, the conversation. If none is found, ask one multiple-choice question
(attach the saved profile / run Setup now) instead of starting Setup unprompted.
When the user changes something (a new minimum pay, a new "avoid"), update the profile block and show it again.

## Per vacancy (max 3)

Same format: multiple-choice, one call. Ask only if the answer can flip the verdict. Good reasons:

- A Must requirement is not in the CV. Question: "The vacancy requires Kubernetes in production. It isn't in your CV." Options: used it in real work · only learned it / small project · never used it.
- A possible blocker you can't verify (location, contract type, a required certificate). Options: yes · no · not sure.
- Two requirements pull in opposite directions and the answer depends on what the user wants.

Bad reasons: curiosity, things the vacancy already answers, things the saved profile already has.
If nothing can flip the verdict, ask nothing and go straight to the analysis.

## If the user answers "used it in real work"

Treat it as a candidate CV addition, not a fact in the CV. Mark it `confirmed by you` in the table
and suggest the exact CV line to add. The user decides whether to add it.
If the answer is "only learned it", the status is `partial`, never `match`.
