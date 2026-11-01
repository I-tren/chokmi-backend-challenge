import json
import threading

import pytest
from chokmi_challenge.llm_runtime import (BudgetExceeded, ImmutableVersionError, IntendedUseError, LLMRuntime,
                                          OutputInvalid, PromptRegistry, PromptVersion, ProviderError)


def pv(version=1, template="Summarise: {text}", use=("summary",), schema=None, mot=100, id="sum"):
    return PromptVersion(id, version, template, frozenset(use), schema or {"summary": str, "score": float}, mot)


class Prov:
    def __init__(self, *outs, tokens=50):
        self.outs, self.tokens, self.prompts = list(outs), tokens, []

    def __call__(self, prompt, max_tokens):
        self.prompts.append(prompt)
        o = self.outs.pop(0) if len(self.outs) > 1 else self.outs[0]
        if isinstance(o, Exception):
            raise o
        return o, self.tokens


GOOD = json.dumps({"summary": "ok", "score": 1})


def rt(prov, ceiling=10**9, price=1000, attempts=3, **kw):
    reg = PromptRegistry()
    reg.register(kw.get("pv") or pv())
    return LLMRuntime(reg, prov, {"t": ceiling}, price, attempts), reg


def test_registry_versions():
    r = PromptRegistry()
    r.register(pv(1))
    r.register(pv(1))  # identical -> no-op
    with pytest.raises(ImmutableVersionError):
        r.register(pv(1, template="changed {text}"))
    with pytest.raises(ValueError):
        r.register(pv(3))
    r.register(pv(2, template="v2 {text}"))
    assert r.get("sum").version == 2 and r.get("sum", 1).version == 1
    with pytest.raises(KeyError):
        r.get("nope")
    with pytest.raises(ValueError):
        r.register(pv(1, id="other", use=()) if False else pv(2, id="fresh"))


def test_happy_path_and_logging():
    p = Prov(GOOD)
    r, _ = rt(p)
    assert r.invoke("t", "sum", {"text": "hi"}, "summary") == {"summary": "ok", "score": 1}
    assert r.spent("t") == 50  # ceil(50 * 1000 / 1000)
    (e,) = r.log
    assert (e["attempt"], e["status"], e["tokens"], e["cost"], e["version"]) == (1, "ok", 50, 50, 1)


def test_intended_use_blocks_before_provider():
    p = Prov(GOOD)
    r, _ = rt(p)
    with pytest.raises(IntendedUseError):
        r.invoke("t", "sum", {"text": "x"}, "eligibility_decision")
    assert p.prompts == [] and r.spent("t") == 0
    assert r.log[0]["status"] == "blocked_use"


def test_variable_contract():
    r, _ = rt(Prov(GOOD))
    with pytest.raises(ValueError):
        r.invoke("t", "sum", {}, "summary")
    with pytest.raises(ValueError):
        r.invoke("t", "sum", {"text": "a", "extra": "b"}, "summary")
    with pytest.raises(ValueError):
        r.invoke("ghost", "sum", {"text": "a"}, "summary")


def test_pii_masked_before_provider():
    p = Prov(GOOD)
    r, _ = rt(p)
    r.invoke("t", "sum", {"text": "Mail jane.doe+x@mail.example.com or call +234 (803) 555-0199 now. Room 12."}, "summary")
    sent = p.prompts[0]
    assert "jane" not in sent and "555" not in sent
    assert "[EMAIL]" in sent and "[PHONE]" in sent
    assert "Room 12" in sent  # short digit runs are not phones


def test_retry_with_repair_and_cost_of_invalid_output():
    p = Prov("not json", json.dumps({"summary": "x"}), GOOD)
    r, _ = rt(p)
    assert r.invoke("t", "sum", {"text": "a"}, "summary")["summary"] == "ok"
    assert [e["status"] for e in r.log] == ["invalid", "invalid", "ok"]
    assert "Previous output invalid" in p.prompts[1] and "Previous output invalid" in p.prompts[2]
    assert p.prompts[1].startswith(p.prompts[0])
    assert r.spent("t") == 150


def test_exhausted_attempts_raise_and_still_charge():
    p = Prov("nope")
    r, _ = rt(p, attempts=2)
    with pytest.raises(OutputInvalid):
        r.invoke("t", "sum", {"text": "a"}, "summary")
    assert len(p.prompts) == 2 and r.spent("t") == 100


@pytest.mark.parametrize("bad", [
    {"summary": "x", "score": True},
    {"summary": "x", "score": "1"},
    {"summary": 5, "score": 1.0},
    {"summary": "x", "score": 1.0, "extra": 1},
    [1, 2],
])
def test_strict_schema(bad):
    r, _ = rt(Prov(json.dumps(bad)), attempts=1)
    with pytest.raises(OutputInvalid):
        r.invoke("t", "sum", {"text": "a"}, "summary")


def test_int_is_acceptable_for_float_but_not_reverse():
    r, _ = rt(Prov(json.dumps({"n": 3.0})), attempts=1, pv=pv(schema={"n": int}, id="sum"))
    with pytest.raises(OutputInvalid):
        r.invoke("t", "sum", {"text": "a"}, "summary")


def test_provider_errors_cost_nothing_and_count_as_attempts():
    p = Prov(ProviderError("503"), GOOD)
    r, _ = rt(p)
    r.invoke("t", "sum", {"text": "a"}, "summary")
    assert [e["status"] for e in r.log] == ["provider_error", "ok"]
    assert r.spent("t") == 50
    p2 = Prov(ProviderError("down"))
    r2, _ = rt(p2, attempts=2)
    with pytest.raises(ProviderError):
        r2.invoke("t", "sum", {"text": "a"}, "summary")
    assert r2.spent("t") == 0


def test_budget_precheck_uses_worst_case():
    # prompt "Summarise: a" = 12 chars -> 3; worst = ceil((3+100)*1000/1000) = 103
    p = Prov(GOOD)
    r, _ = rt(p, ceiling=102)
    with pytest.raises(BudgetExceeded):
        r.invoke("t", "sum", {"text": "a"}, "summary")
    assert p.prompts == [] and r.log[0]["status"] == "blocked_budget"
    r2, _ = rt(Prov(GOOD), ceiling=103)
    r2.invoke("t", "sum", {"text": "a"}, "summary")


def test_budget_rechecked_on_every_retry():
    p = Prov("bad")
    r, _ = rt(p, ceiling=250, attempts=5)  # each attempt reserves 103+, actual 50
    with pytest.raises(BudgetExceeded):
        r.invoke("t", "sum", {"text": "a"}, "summary")
    assert 1 <= len(p.prompts) < 5
    assert r.spent("t") <= 250


def test_ceiling_never_exceeded_under_concurrency():
    p = Prov(GOOD, tokens=100)
    reg = PromptRegistry()
    reg.register(pv())
    r = LLMRuntime(reg, p, {"t": 2000}, 1000)
    outcomes = []

    def go():
        try:
            r.invoke("t", "sum", {"text": "a"}, "summary")
            outcomes.append("ok")
        except BudgetExceeded:
            outcomes.append("blocked")

    ts = [threading.Thread(target=go) for _ in range(60)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert r.spent("t") <= 2000
    assert outcomes.count("ok") == len(p.prompts)
    assert outcomes.count("ok") >= 1 and "blocked" in outcomes
