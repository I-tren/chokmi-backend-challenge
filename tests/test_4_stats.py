import math
import random

import pytest
from chokmi_challenge.stats import auto_accept_threshold, cohens_kappa, review_load, wilson_lower


def test_kappa_known_values():
    a = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
    b = ["y"] * 20 + ["y"] * 5 + ["n"] * 10 + ["n"] * 15
    assert cohens_kappa(a, b) == pytest.approx(0.4, abs=1e-9)
    assert cohens_kappa(list("abab"), list("abab")) == 1.0
    assert cohens_kappa(["x"] * 5, ["x"] * 5) == 1.0
    assert cohens_kappa(list("aabb"), list("bbaa")) == pytest.approx(-1.0)


def test_kappa_multiclass_and_asymmetric_labels():
    a = ["a", "b", "c", "a", "b", "c"]
    b = ["a", "b", "c", "b", "b", "a"]
    po = 4 / 6
    pe = (2 * 2 + 2 * 3 + 2 * 1) / 36
    assert cohens_kappa(a, b) == pytest.approx((po - pe) / (1 - pe))
    assert cohens_kappa(["a", "a"], ["b", "b"]) == pytest.approx(0.0)  # pe = 0


@pytest.mark.parametrize("a,b", [([], []), (["a"], ["a", "b"])])
def test_kappa_errors(a, b):
    with pytest.raises(ValueError):
        cohens_kappa(a, b)


def test_wilson():
    assert wilson_lower(0, 0) == 0.0
    assert wilson_lower(50, 100) == pytest.approx(0.4038, abs=5e-4)
    assert wilson_lower(100, 100) == pytest.approx(0.9630, abs=5e-4)
    assert wilson_lower(0, 10) == pytest.approx(0.0, abs=1e-9)
    assert wilson_lower(95, 100) < wilson_lower(950, 1000) < 0.95


def synth(n, seed, noise=0.0):
    rng = random.Random(seed)
    items = []
    for _ in range(n):
        s = round(rng.random(), 2)
        items.append((s, rng.random() < 0.35 + 0.65 * s ** 2))
    return items


def test_threshold_order_invariant_and_valid():
    items = synth(3000, 7)
    t = auto_accept_threshold(items, 0.90)
    assert t is not None
    for s in range(5):
        sh = items[:]
        random.Random(s).shuffle(sh)
        assert auto_accept_threshold(sh, 0.90) == t
    acc = [c for s, c in items if s >= t]
    assert wilson_lower(sum(acc), len(acc)) >= 0.90
    # maximal coverage: every lower observed score must fail
    for cand in sorted({s for s, _ in items}):
        if cand < t:
            a = [c for s, c in items if s >= cand]
            assert len(a) < 30 or wilson_lower(sum(a), len(a)) < 0.90


def test_threshold_picks_non_monotone_best():
    # high band clean, middle band dirty, low band clean-ish but huge: precision is NOT monotone
    items = [(0.9, True)] * 60 + [(0.6, False)] * 600 + [(0.3, True)] * 5000
    t = auto_accept_threshold(items, 0.90)
    assert t == 0.9  # accepting down to 0.3 drags in 600 failures (~89% precise)


def test_threshold_ties_not_split_and_min_n():
    items = [(0.8, True)] * 29 + [(0.7, True)] * 40
    assert auto_accept_threshold(items, 0.8) == 0.7
    assert auto_accept_threshold(items[:29], 0.1) is None  # < min_n
    assert auto_accept_threshold(items[:29], 0.1, min_n=10) == 0.8
    assert auto_accept_threshold([(0.5, False)] * 500, 0.5) is None
    assert auto_accept_threshold([], 0.5) is None


def test_threshold_equal_coverage_prefers_higher_t():
    items = [(0.9, True)] * 100
    assert auto_accept_threshold(items, 0.9) == 0.9


def test_nan_rejected():
    with pytest.raises(ValueError):
        auto_accept_threshold([(float("nan"), True)] * 40, 0.5)


def test_review_load():
    items = [(0.9, True), (0.9, False), (0.5, True), (0.4, False)]
    assert review_load(items, 0.9) == {"auto": 2, "review": 2, "auto_precision": 0.5}
    assert review_load(items, 0.99) == {"auto": 0, "review": 4, "auto_precision": None}
