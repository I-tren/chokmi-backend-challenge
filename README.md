# Chokmi — Backend Engineering Challenge

Chokmi is a research-operations platform: it ingests survey and interview data,
uses AI to code open-text answers, meters that AI against prepaid wallets, and
signs the claims it releases so a reviewer can verify them later. This challenge
is built from five real problems in that system, stripped of any proprietary
code. It is meant to be **hard**. Most strong candidates will not finish all of
it, and that is fine. We read how you reason about what you don't finish.

**Time:** 6 hours of focused work, from your first commit. Push as you go; we
read the history. **Language:** Python 3.11+, standard library only for the
solution code (`pytest` is the only dependency). No other packages.

## What to do

| Part | File | Topic | Points |
|---|---|---|---|
| 1 | `chokmi_challenge/robots.py` | RFC 9309 robots.txt matcher for the evidence crawler | 15 |
| 2 | `chokmi_challenge/wallet.py` | Idempotent, concurrent prepaid wallet over out-of-order events | 25 |
| 3 | `chokmi_challenge/llm_runtime.py` | Governed LLM invoker: prompt registry, PII masking, cost ceiling, retries | 25 |
| 4 | `chokmi_challenge/stats.py` | Coding agreement and an evidence-based auto-accept band | 15 |
| 5 | `chokmi_challenge/passport.py` | Canonical JSON, key-rotating signatures, stability score | 10 |
| 6 | `DESIGN.md` | Written design and judgement questions | 10 |

Each module's docstring is the specification. Where it says "must", a test
probably checks it. The visible tests are a floor, not the grade: our graded run
adds tests we don't show you, around concurrency, malformed input and the edges
of each spec. Write your own tests for anything the spec leaves open, and say in
`DESIGN.md` what you assumed.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                      # all parts
pytest tests/test_2_wallet.py
```

## How to submit

1. Click **Use this template → Create a new repository** on the repo page.
   Owner: your own account. Visibility: **Private**. Please don't use *Fork*:
   a fork of a public repo is public, and your solution is not for sharing.
2. Clone your copy, work on it, and push as you go (we read the commit history).
3. Invite **fakay96** to your private repo as a collaborator (Settings →
   Collaborators) and email us the repo link when you're done or when your
   6 hours are up. Anything pushed after that is ignored.

The *Visible tests* check in your repo's Actions tab runs the tests you can see.
Your score comes from our own run, which includes tests you can't see.

## Rules

* Do not edit anything under `tests/` that is already there. Adding new test
  files is encouraged.
* Do not change a public signature. Add helpers freely.
* Use of AI assistants is allowed, but you are responsible for every line. In
  `DESIGN.md` Q6 you will be asked to explain and defend choices. Code you can't
  explain will cost you more than code that is missing.
* Don't publish your solution or this repo.

## How we grade

Correctness against the visible and hidden tests (Parts 1–5), then a human
review of design clarity, concurrency reasoning, error handling and tests you
wrote yourself. Part 6 is read by an engineer, not a script.
