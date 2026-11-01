import itertools
import random
import threading

import pytest
from chokmi_challenge.wallet import ConflictError, Wallet


def ev(i, t, ty, a, ref=None, tenant="t1"):
    e = {"id": i, "tenant": tenant, "type": ty, "amount": a}
    if ref:
        e["ref"] = ref
    return e


def test_basic_flow_and_ledger():
    w = Wallet()
    assert w.apply(ev("e1", 0, "topup", 100)) == "applied"
    assert w.apply(ev("e2", 0, "charge", 30)) == "applied"
    assert w.apply(ev("e3", 0, "charge", 100)) == "rejected"
    assert w.balance("t1") == 70
    assert w.ledger("t1") == [("e1", "topup", 100), ("e2", "charge", -30)]
    assert w.balance("nobody") == 0 and w.ledger("nobody") == []


def test_idempotent_and_conflict():
    w = Wallet()
    w.apply(ev("e1", 0, "topup", 100))
    assert w.apply(ev("e1", 0, "topup", 100)) == "applied"
    assert w.balance("t1") == 100
    with pytest.raises(ConflictError):
        w.apply(ev("e1", 0, "topup", 101))
    assert w.balance("t1") == 100


def test_rejected_charge_is_never_upgraded_by_replay():
    w = Wallet()
    assert w.apply(ev("c1", 0, "charge", 50)) == "rejected"
    w.apply(ev("t1", 0, "topup", 500))
    assert w.apply(ev("c1", 0, "charge", 50)) == "rejected"
    assert w.balance("t1") == 500
    assert w.status("c1") == "rejected"


@pytest.mark.parametrize("bad", [0, -5, 1.5, "10", True, None])
def test_amount_validation(bad):
    with pytest.raises(ValueError):
        Wallet().apply(ev("x", 0, "topup", bad))


def test_refund_before_charge_is_pending_then_applied():
    w = Wallet()
    w.apply(ev("t", 0, "topup", 100))
    assert w.apply(ev("r1", 0, "refund", 20, ref="c1")) == "pending"
    assert w.balance("t1") == 100
    assert w.apply(ev("c1", 0, "charge", 60)) == "applied"
    assert w.status("r1") == "applied"
    assert w.balance("t1") == 100 - 60 + 20
    assert [x[0] for x in w.ledger("t1")] == ["t", "c1", "r1"]


def test_pending_refund_rejected_when_charge_rejected():
    w = Wallet()
    w.apply(ev("r1", 0, "refund", 20, ref="c1"))
    assert w.apply(ev("c1", 0, "charge", 60)) == "rejected"
    assert w.status("r1") == "rejected"
    assert w.balance("t1") == 0


def test_refund_cap_and_arrival_order():
    w = Wallet()
    w.apply(ev("t", 0, "topup", 100))
    w.apply(ev("c", 0, "charge", 50))
    assert w.apply(ev("r1", 0, "refund", 30, ref="c")) == "applied"
    assert w.apply(ev("r2", 0, "refund", 30, ref="c")) == "rejected"
    assert w.apply(ev("r3", 0, "refund", 20, ref="c")) == "applied"
    assert w.balance("t1") == 100


def test_pending_refunds_judged_in_arrival_order():
    w = Wallet()
    w.apply(ev("t", 0, "topup", 100))
    w.apply(ev("r1", 0, "refund", 40, ref="c"))
    w.apply(ev("r2", 0, "refund", 40, ref="c"))
    w.apply(ev("c", 0, "charge", 50))
    assert w.status("r1") == "applied" and w.status("r2") == "rejected"
    assert w.balance("t1") == 100 - 50 + 40


def test_refund_of_non_charge_rejected():
    w = Wallet()
    w.apply(ev("t", 0, "topup", 100))
    assert w.apply(ev("r", 0, "refund", 10, ref="t")) == "rejected"
    assert w.balance("t1") == 100


def test_cross_tenant_isolation_and_refund_attack():
    w = Wallet()
    w.apply(ev("ta", 0, "topup", 100, tenant="A"))
    w.apply(ev("ca", 0, "charge", 80, tenant="A"))
    assert w.apply(ev("evil", 0, "refund", 80, ref="ca", tenant="B")) == "rejected"
    assert w.balance("B") == 0 and w.balance("A") == 20
    assert w.ledger("B") == []
    # a cross-tenant refund that arrives BEFORE the charge must also fail
    w2 = Wallet()
    w2.apply(ev("evil", 0, "refund", 80, ref="ca", tenant="B"))
    w2.apply(ev("ta", 0, "topup", 100, tenant="A"))
    w2.apply(ev("ca", 0, "charge", 80, tenant="A"))
    assert w2.status("evil") == "rejected" and w2.balance("B") == 0


def test_conflict_on_pending_refund_replay():
    w = Wallet()
    w.apply(ev("r", 0, "refund", 10, ref="c"))
    assert w.apply(ev("r", 0, "refund", 10, ref="c")) == "pending"
    with pytest.raises(ConflictError):
        w.apply(ev("r", 0, "refund", 10, ref="other"))


def test_concurrent_charges_conserve_money():
    w = Wallet()
    w.apply(ev("seed", 0, "topup", 1000))
    results = []

    def go(k):
        for j in range(50):
            results.append(w.apply(ev(f"c{k}-{j}", 0, "charge", 7)))

    ts = [threading.Thread(target=go, args=(k,)) for k in range(32)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    applied = results.count("applied")
    assert applied == 1000 // 7
    assert w.balance("t1") == 1000 - 7 * applied >= 0
    assert sum(d for _, _, d in w.ledger("t1")) == w.balance("t1")


def test_concurrent_duplicate_delivery_applies_once():
    w = Wallet()
    w.apply(ev("seed", 0, "topup", 100))
    e = ev("same", 0, "charge", 10)
    ts = [threading.Thread(target=lambda: w.apply(dict(e))) for _ in range(64)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert w.balance("t1") == 90


def test_refund_ordering_permutations_converge():
    base = [ev("t", 0, "topup", 100), ev("c", 0, "charge", 60),
            ev("r1", 0, "refund", 10, ref="c"), ev("r2", 0, "refund", 10, ref="c")]
    outcomes = set()
    for perm in itertools.permutations(base):
        order = [e["id"] for e in perm]
        # only orders where the topup precedes the charge are meaningful
        if order.index("t") > order.index("c"):
            continue
        w = Wallet()
        for e in perm:
            w.apply(e)
        outcomes.add((w.balance("t1"), w.status("r1"), w.status("r2")))
    assert outcomes == {(60, "applied", "applied")}
