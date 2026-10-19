"""Small statistics helpers (no SciPy): Welch and paired t-tests, confidence
intervals and an effect size, for comparing controllers over repeated
evaluation episodes.

The p-value comes from the Student t distribution, evaluated through the
regularised incomplete beta function (continued-fraction form).
"""

import math


def _betacf(a: float, b: float, x: float, max_iter: int = 300, eps: float = 3e-14) -> float:
    """Continued fraction for the incomplete beta function (modified Lentz)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def betai(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_front = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                + a * math.log(x) + b * math.log(1.0 - x))
    front = math.exp(ln_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_two_sided_p(t: float, df: float) -> float:
    """Two-sided p-value of a Student t statistic."""
    if df <= 0 or math.isnan(t):
        return float("nan")
    if math.isinf(t):
        return 0.0
    return betai(df / 2.0, 0.5, df / (df + t * t))


def t_critical(df: float, confidence: float = 0.95) -> float:
    """Two-sided critical value (e.g. about 2.228 for df=10 at 95 percent)."""
    target = 1.0 - confidence
    lo, hi = 0.0, 1000.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if t_two_sided_p(mid, df) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def mean(values) -> float:
    values = list(values)
    return sum(values) / len(values)


def sample_var(values) -> float:
    values = list(values)
    m = mean(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - 1) if len(values) > 1 else 0.0


def ci95(values) -> tuple:
    """(mean, half-width of the 95 percent confidence interval of the mean)."""
    values = list(values)
    n = len(values)
    m = mean(values)
    if n < 2:
        return m, float("nan")
    return m, t_critical(n - 1) * math.sqrt(sample_var(values) / n)


def welch_t_test(a, b) -> dict:
    """Independent two-sample t-test without assuming equal variances.
    `t` is positive when the mean of `a` exceeds the mean of `b`."""
    a, b = list(a), list(b)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        raise ValueError("need at least two observations per group")
    va, vb = sample_var(a) / na, sample_var(b) / nb
    diff = mean(a) - mean(b)
    se = math.sqrt(va + vb)
    if se == 0.0:
        return {"t": 0.0 if diff == 0 else math.copysign(float("inf"), diff), "df": na + nb - 2,
                "p": 1.0 if diff == 0 else 0.0, "diff": diff}
    t = diff / se
    df = (va + vb) ** 2 / ((va ** 2) / (na - 1) + (vb ** 2) / (nb - 1))
    return {"t": t, "df": df, "p": t_two_sided_p(t, df), "diff": diff}


def paired_t_test(a, b) -> dict:
    """Paired t-test on per-episode differences (same traffic seed for both
    controllers). `t` is positive when `a` exceeds `b` on average."""
    a, b = list(a), list(b)
    if len(a) != len(b) or len(a) < 2:
        raise ValueError("paired test needs two equal-length samples with at least two items")
    diffs = [x - y for x, y in zip(a, b)]
    n = len(diffs)
    se = math.sqrt(sample_var(diffs) / n)
    d = mean(diffs)
    if se == 0.0:
        return {"t": 0.0 if d == 0 else math.copysign(float("inf"), d), "df": n - 1,
                "p": 1.0 if d == 0 else 0.0, "diff": d}
    t = d / se
    return {"t": t, "df": n - 1, "p": t_two_sided_p(t, n - 1), "diff": d}


def cohens_d(a, b) -> float:
    """Standardised difference (pooled standard deviation); positive when mean(a) > mean(b)."""
    a, b = list(a), list(b)
    na, nb = len(a), len(b)
    pooled = math.sqrt(((na - 1) * sample_var(a) + (nb - 1) * sample_var(b)) / (na + nb - 2))
    diff = mean(a) - mean(b)
    if pooled == 0.0:
        return 0.0 if diff == 0 else math.copysign(float("inf"), diff)
    return diff / pooled
