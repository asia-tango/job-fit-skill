# Expected output (shape, not exact words)

Input: `cv.md` + `vacancy.txt`. The quotes below are copied from those two files
and pass `scripts/verify_quotes.py`.

**Verdict** – ❓ needs a check first. The vacancy is UK-located and says nothing about work authorization.
If it can't be done from outside the UK, stop here.

**What would change the verdict** – written confirmation that the role can be done remotely from the candidate's country, as a contractor.

**Requirements vs CV**

| Requirement | Evidence in CV | Status |
|---|---|---|
| "8+ years of professional software engineering experience" | "Frontend engineer, 6 years, mostly Angular and TypeScript" | ❌ gap (6 vs 8+, by the CV dates) |
| "Deep proficiency in TypeScript and React or Angular" | "Angular, TypeScript, RxJS, NgRx, AG Grid, Jasmine, Karma, Git" | ✅ match (Angular side) |
| "Experience building real-time, asynchronous, event-driven user experiences" | "Added real-time updates over WebSocket" | ✅ match |
| "Mentor and coach engineers" | "Reviewed code and mentored two junior developers" | ⚠️ partial (two juniors, no lead role) |
| "lead complex initiatives" | — | ❓ not in CV – ask: did you lead any initiative end to end? |

**Fix in the CV**
1. Move "Added real-time updates over WebSocket" to the top of the Acme Analytics bullets. It is the closest match to the core of this vacancy.
2. If you really led a migration or a design decision, say so with the scope ("Migrated AngularJS modules to Angular" has no size or role yet). Add only if true.

**Growth**
- Stated: architecture influence, standards, mentoring – a step up from the CV's scope.
- Guess: streaming and typing states in a conversational UI are a new problem on familiar tools.
- Can't tell: who decides architecture today.

**Red flags** – "Primarily remote, occasional office visits" in the UK. "Fast-paced environment" with no process described.

**Money and format** – not stated. Contract type for a non-UK contractor not stated.

**Questions to ask**
- Can this be done from outside the UK, and as what – employee or contractor? (decides if it's possible)
- Is "8+ years" a hard requirement or a guide? (a stretch or a miss)
- Who owns frontend architecture decisions today? (what would be mine)
- How often are the office visits and who pays? (cost and time)
- What is the salary range, gross or net? (not stated)

**Talking points for the application**
1. Start with real-time. Backs: "Added real-time updates over WebSocket". Answers: "Experience building real-time, asynchronous, event-driven user experiences".
2. Mentoring, said as it was. Backs: "Reviewed code and mentored two junior developers". Answers: "Mentor and coach engineers".
3. Angular depth. Backs: "Built data-heavy dashboards in Angular with RxJS and NgRx". Answers: "Deep proficiency in TypeScript and React or Angular".
4. The gap, honestly: six years against "8+ years of professional software engineering experience"; say it plainly and point to the scope instead.
5. Check before writing: React is not in the CV. Don't mention it unless you have used it.
