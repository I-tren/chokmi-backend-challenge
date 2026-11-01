"""Part 5 — signed claim passports.

Chokmi signs a "passport" for every claim it releases, so a regulator can
verify it later, possibly after keys were rotated.

canonical_json(obj) -> bytes
    Deterministic UTF-8 JSON: keys sorted by code point, no whitespace,
    non-ASCII emitted raw (not \\u-escaped), all strings (keys included)
    Unicode-NFC normalised. Two keys that collide after NFC -> ValueError.
    Numbers: NaN/Infinity -> ValueError; a float with an integral value is
    emitted as an integer ("1.0" -> "1", "-0.0" -> "0"); other floats use the
    shortest round-trip repr; ints with abs value > 2**53 -> ValueError (they
    are not safe for JS verifiers). bool stays true/false (never 1/0). tuples
    behave like lists. Non-str keys, or any other type -> ValueError.

sign(payload, keyring, active_kid) -> dict
    keyring: dict[str kid -> bytes secret]. Returns
    {"payload": payload, "kid": active_kid, "sig": <hex HMAC-SHA256>} over
    b"chokmi-passport-v1\\0" + kid.encode() + b"\\0" + canonical_json(payload).

verify(envelope, keyring, revoked=frozenset()) -> bool
    True only if the kid is in the keyring, not revoked, and the signature
    matches (constant-time compare). NEVER raises: malformed envelopes,
    wrong types, non-hex signatures, unserialisable payloads all -> False.
    Payload key order or equivalent Unicode forms must not matter; a changed
    value, a swapped kid, or a signature reused on another payload must fail.

stability_score(base_effect, perturbed_effects) -> float
    Share of perturbed effects that keep the same sign as base_effect AND have
    abs >= 0.5 * abs(base_effect). base_effect == 0 -> 0.0. Empty list or any
    NaN -> ValueError.
"""


def canonical_json(obj):
    raise NotImplementedError


def sign(payload, keyring, active_kid):
    raise NotImplementedError


def verify(envelope, keyring, revoked=frozenset()):
    raise NotImplementedError


def stability_score(base_effect, perturbed_effects):
    raise NotImplementedError
