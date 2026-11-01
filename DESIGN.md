# DESIGN.md — written section (10 points)

Answer in your own words. Be specific, with names, numbers and trade-offs. Short
and precise beats long and vague. About 1 page total is plenty; ~150 words each.

## Q1. Assumptions
List every place the specs were ambiguous and what you assumed. Which one would
you most want to confirm with the product owner before shipping?

## Q2. Wallet at 50M rows
`Wallet` is in-memory. In production the ledger is a Postgres table that has
reached 50M rows, events come from a webhook endpoint behind several app
servers, and Celery retries tasks. Describe how you would make `apply`
idempotent and race-free there (constraints, locking or isolation, the
idempotency key's lifetime), and how you would add a NOT NULL column to that
table with no downtime.

## Q3. Cost ceilings
In `LLMRuntime` you charge on worst-case before the call and reconcile after.
A tenant says they were blocked while "well under budget". Explain why that can
happen by design, how you'd confirm it from the log, and one change that
reduces false blocks without ever letting spend exceed the ceiling.

## Q4. The 0.82 problem
Our AI's confidence score of 0.82 was measured as only ~50% precise on real
data, and results moved by several F1 points just from the order batches were
processed in. (a) What does that tell you about using the model's own score as
a gate? (b) How would you evaluate an auto-accept threshold honestly, given you
only have 400 human-coded answers? (c) What would make you refuse to ship it?

## Q5. A regulator's question
A signed passport from 14 months ago must still verify, but key `k1` was later
found to have leaked. What should happen to passports signed with `k1`? What do
you tell the regulator, and what does your `verify` need to support so that you
can answer honestly? Mention the limits of HMAC here and what you would use
instead.

## Q6. Defend one decision
Pick the single design decision in your code you are least sure about. Say what
the alternative was, why you chose what you chose, and what evidence would make
you reverse it. If you used an AI assistant, name one suggestion you rejected
and why.
