"""Part 2 — prepaid AI wallet fed by an at-least-once, out-of-order event stream.

Chokmi meters AI usage against a prepaid wallet while Stripe-style events
arrive duplicated, late, and concurrently. Implement `Wallet`.

Event: dict with keys
    id      str, globally unique event id
    tenant  str
    type    "topup" | "charge" | "refund"
    amount  int, strictly positive, in micro-units (bool/float/str -> ValueError)
    ref     str, refunds only: the *event id of the charge* being refunded

    Wallet.apply(event) -> str   one of "applied", "rejected", "pending"
    Wallet.status(event_id) -> str | None   current status of a seen event
    Wallet.balance(tenant) -> int
    Wallet.ledger(tenant) -> list[tuple[str, str, int]]
                              (event_id, type, signed_delta) in APPLY order

Semantics:
* Idempotent by event id. Re-applying an identical event returns its original
  status and changes nothing. Re-using an id with a different payload raises
  `ConflictError`. A replay never "upgrades" a rejected charge, even if later
  top-ups would now cover it.
* topup: always applied. charge: applied iff balance >= amount, else rejected
  (balance never goes negative, under any interleaving of threads).
* refund: credits the charge's amount back. If the referenced charge has not
  been seen yet the refund is "pending" and is applied automatically (and
  `status()` flips to "applied") once that charge is applied. If that charge is
  later *rejected* the pending refund becomes "rejected".
  Total refunds against one charge may not exceed the charge: a refund that
  would push the total over is "rejected" (a pending one is judged when it
  becomes applicable, in arrival order).
* A refund whose ref is a charge of a DIFFERENT tenant is rejected, and must
  never reveal or alter the other tenant's data.
* Tenants are fully isolated: ledger/balance of one never include another's.
* Fully thread-safe: 32 threads hammering one tenant must conserve money
  exactly.
"""


class ConflictError(Exception):
    pass


class Wallet:
    def apply(self, event):
        raise NotImplementedError

    def status(self, event_id):
        raise NotImplementedError

    def balance(self, tenant):
        raise NotImplementedError

    def ledger(self, tenant):
        raise NotImplementedError
