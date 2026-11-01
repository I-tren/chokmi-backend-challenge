import hashlib
import hmac
import json

import pytest
from chokmi_challenge.passport import canonical_json, sign, stability_score, verify

KR = {"k1": b"secret-one", "k2": b"secret-two"}


def test_canonical_basics():
    assert canonical_json({"b": 1, "a": [True, None, 2.5]}) == b'{"a":[true,null,2.5],"b":1}'
    assert canonical_json({"a": (1, 2)}) == b'{"a":[1,2]}'
    assert canonical_json({"z": 1.0, "y": -0.0, "x": 1e3}) == b'{"x":1000,"y":0,"z":1}'
    assert canonical_json({"k": "café ✓"}) == '{"k":"café ✓"}'.encode()
    assert canonical_json("a\"b\n") == b'"a\\"b\\n"'


def test_canonical_bool_is_not_int():
    assert canonical_json([True, 1, False, 0]) == b"[true,1,false,0]"


def test_canonical_nfc_and_collisions():
    nfd = "café"
    assert canonical_json({"k": nfd}) == canonical_json({"k": "café"})
    assert canonical_json({nfd: 1}) == canonical_json({"café": 1})
    with pytest.raises(ValueError):
        canonical_json({nfd: 1, "café": 2})


def test_canonical_sorted_by_codepoint():
    assert canonical_json({"b": 1, "B": 2, "é": 3, "a": 4}) == '{"B":2,"a":4,"b":1,"é":3}'.encode()


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), 2 ** 53 + 1, -(2 ** 60),
                                 {1: "x"}, {"a": {1, 2}}, b"bytes", object()])
def test_canonical_rejects(bad):
    with pytest.raises(ValueError):
        canonical_json(bad)


def test_canonical_edge_numbers_ok():
    assert canonical_json([2 ** 53, -(2 ** 53), 0.1, 1e-7, 123456789.125]) == b"[9007199254740992,-9007199254740992,0.1,1e-07,123456789.125]"


def test_sign_exact_construction():
    p = {"claim": "x", "n": 3}
    env = sign(p, KR, "k1")
    msg = b"chokmi-passport-v1\0k1\0" + canonical_json(p)
    assert env["sig"] == hmac.new(KR["k1"], msg, hashlib.sha256).hexdigest()
    assert env["kid"] == "k1" and env["payload"] == p


def test_verify_roundtrip_order_and_unicode_insensitive():
    env = sign({"a": 1, "b": "café"}, KR, "k1")
    assert verify(env, KR)
    env2 = {**env, "payload": {"b": "café", "a": 1.0}}
    assert verify(env2, KR)


def test_verify_tamper_and_key_games():
    env = sign({"a": 1}, KR, "k1")
    assert not verify({**env, "payload": {"a": 2}}, KR)
    assert not verify({**env, "kid": "k2"}, KR)                # swapped kid
    assert not verify({**env, "kid": "k9"}, KR)                # unknown
    assert not verify(env, KR, revoked={"k1"})                 # revoked
    other = sign({"a": 2}, KR, "k1")
    assert not verify({**env, "sig": other["sig"]}, KR)         # sig reuse
    assert verify(env, {**KR, "k3": b"new"})                    # rotation keeps old keys verifying
    assert not verify(env, {"k1": b"rotated-secret"})


def test_domain_separation():
    # a raw HMAC over the payload alone (no prefix/kid) must not verify
    p = {"a": 1}
    naive = hmac.new(KR["k1"], canonical_json(p), hashlib.sha256).hexdigest()
    assert not verify({"payload": p, "kid": "k1", "sig": naive}, KR)


@pytest.mark.parametrize("bad", [
    None, "str", 5, [], {}, {"kid": "k1"}, {"payload": {}, "kid": "k1"},
    {"payload": {}, "kid": 7, "sig": "00"}, {"payload": {}, "kid": "k1", "sig": 12},
    {"payload": {}, "kid": "k1", "sig": "zz-not-hex"}, {"payload": {"x": float("nan")}, "kid": "k1", "sig": "00"},
    {"payload": {"x": object()}, "kid": "k1", "sig": "00"}, {"payload": {}, "kid": ["k1"], "sig": "00"},
])
def test_verify_never_raises(bad):
    assert verify(bad, KR) is False


def test_stability():
    assert stability_score(1.0, [0.9, 0.5, 0.49, -0.9, 0.0, 2.0]) == pytest.approx(3 / 6)
    assert stability_score(-2.0, [-1.0, -0.99, 1.0]) == pytest.approx(1 / 3)
    assert stability_score(0.0, [1, 2]) == 0.0
    for bad in ([], [float("nan")]):
        with pytest.raises(ValueError):
            stability_score(1.0, bad)
