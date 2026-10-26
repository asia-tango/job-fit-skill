# Expected output (shape, not exact words)

Input: `cv.md` + `vacancy.txt`. Quotes are copied from those files and pass `scripts/verify_quotes.py`.

**Verdict** – ❓ needs a check first. The vacancy is "EU only" and the CV doesn't say where the candidate can work.

**What would change the verdict** – confirmation that the role can be done as a contractor from the candidate's country, or a right to work in the EU.

**Requirements vs CV**

| Requirement | Evidence in CV | Status |
|---|---|---|
| "5+ years of backend development in Go or Python" | "Backend engineer, 7 years, mostly Python and PostgreSQL" | ✅ match |
| "Experience with high-load distributed systems" | "Designed REST APIs in Python (FastAPI) serving 2M requests per day" | ⚠️ partial (load yes; "distributed" is shown only by Kafka consumers) |
| "Hands-on Kubernetes in production" | "Python, FastAPI, PostgreSQL, Kafka, Docker, AWS (EC2, RDS), Git" | ❓ not in CV – ask (Docker is listed, Kubernetes is not) |
| "Mentor mid-level engineers" | — | ❓ not in CV – ask. The CV shows "Led the on-call rotation for a team of five", which is leadership but not mentoring |
| "Experience with payment systems or PCI DSS is a plus" | — | ❌ gap (nice to have) |

**Fix in the CV**
1. Move "Designed REST APIs in Python (FastAPI) serving 2M requests per day" to the top. It answers the main requirement.
2. If you did mentor people, say who and for how long. Add it only if true.
3. If you used Kubernetes (even through a managed service), name it and what you did with it. Add only if true.

**Growth**
- Stated: payments domain, mentoring mid-level engineers.
- Guess: payments adds reliability and compliance work that the CV doesn't show yet.
- Can't tell: who owns on-call and incident response.

**Red flags** – "Remote within the EU only". The salary is in EUR, gross.

**Money and format** – "Salary: 5000-6500 EUR gross" is stated by the company. Contract type for a non-EU candidate is not stated.

**Questions to ask**
- Can this be done as a contractor from outside the EU? (decides if it is possible at all)
- How is on-call organized and how often are pages? (the CV shows on-call leadership; this is the load)
- How much of the work is Kubernetes? (a real gap or a small share)
- How many engineers and how many mid-level ones would I mentor? (scope)

**Talking points for the application**
1. Lead with scale. Backs: "Designed REST APIs in Python (FastAPI) serving 2M requests per day". Answers: "Experience with high-load distributed systems".
2. Years and language. Backs: "Backend engineer, 7 years, mostly Python and PostgreSQL". Answers: "5+ years of backend development in Go or Python".
3. A reliability example. Backs: "Reduced slow query time by 60% after adding indexes and rewriting reports".
4. The gap, said plainly: Kubernetes in production is not in the CV; point to the closest real experience (Docker, AWS) only if you used them for deployment.
5. Check before writing: PCI DSS and mentoring are not in the CV. Don't mention them unless true.
