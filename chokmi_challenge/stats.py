"""Part 4 — qualitative-coding agreement and the auto-accept band.

Chokmi's AI codes open-text answers; humans review the uncertain ones. We
measured that a naive "score >= 0.82 is auto-accepted" band was only ~50%
precise, so the band must be derived from evidence, not picked.

cohens_kappa(a, b) -> float
    Two equal-length, non-empty label sequences. Labels are hashable. Standard
    Cohen's kappa. If chance agreement is 1.0 (both raters use one identical
    label throughout) return 1.0. Length mismatch or empty -> ValueError.

wilson_lower(successes, n, z=1.96) -> float
    Lower bound of the Wilson score interval; n == 0 -> 0.0.

auto_accept_threshold(items, target_precision, z=1.96, min_n=30) -> float | None
    items: iterable of (score: float, is_correct: bool) from a HELD-OUT set.
    Return the threshold t such that accepting every item with score >= t
    satisfies BOTH n_accepted >= min_n AND
    wilson_lower(correct_accepted, n_accepted, z) >= target_precision, choosing
    the t that accepts the MOST items (ties: the higher t). Candidate
    thresholds are the distinct observed scores only; items with equal scores
    are never split. None if no threshold qualifies. The result must not depend
    on input order. NaN scores -> ValueError.

review_load(items, threshold) -> dict
    {"auto": n, "review": n, "auto_precision": float | None} where
    auto_precision is the empirical precision of the auto-accepted set (None
    if empty).
"""


def cohens_kappa(a, b):
    raise NotImplementedError


def wilson_lower(successes, n, z=1.96):
    raise NotImplementedError


def auto_accept_threshold(items, target_precision, z=1.96, min_n=30):
    raise NotImplementedError


def review_load(items, threshold):
    raise NotImplementedError
