"""Explainable lost/found matching engine. Pure Python: no Django imports, so it is unit-testable alone.

Weighted components (all configurable): category, text (TF-IDF cosine), location, date, visual.
Components that cannot be computed are dropped and the remaining weights are renormalised,
so a missing photo never sinks an otherwise good match.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime

DEFAULT_WEIGHTS = {"category": 0.20, "text": 0.25, "location": 0.20, "date": 0.15, "visual": 0.20}
STOPWORDS = frozenset("""a an the and or of to in on at is it its was were with for from my i me this that has have had
been by as are be near lost found item left small big new old one very please""".split())


def tokenize(text):
    tokens = []
    for tok in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if tok in STOPWORDS or len(tok) < 2:
            continue
        if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
            tok = tok[:-1]
        tokens.append(tok)
    return tokens


def text_similarities(query_text, candidate_texts):
    """TF-IDF cosine similarity of query vs each candidate. None where either side has no tokens."""
    docs = [tokenize(query_text)] + [tokenize(t) for t in candidate_texts]
    n = len(docs)
    df = Counter()
    for d in docs:
        df.update(set(d))
    idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}

    def vec(tokens):
        tf = Counter(tokens)
        return {t: (1 + math.log(c)) * idf[t] for t, c in tf.items()}

    vectors = [vec(d) for d in docs]
    q = vectors[0]
    qn = math.sqrt(sum(v * v for v in q.values()))
    out = []
    for d, v in zip(docs[1:], vectors[1:]):
        vn = math.sqrt(sum(x * x for x in v.values()))
        if not docs[0] or not d or qn == 0 or vn == 0:
            out.append(None)
            continue
        out.append(sum(w * v.get(t, 0.0) for t, w in q.items()) / (qn * vn))
    return out


def shared_keywords(a_text, b_text, limit=5):
    common = set(tokenize(a_text)) & set(tokenize(b_text))
    return sorted(common)[:limit]


def category_score(a, b):
    """1.0 same category, 0.5 same group, 0.25 if either is 'other'; None = incompatible (excluded)."""
    if a.get("category_id") == b.get("category_id"):
        return 1.0
    ga, gb = a.get("category_group"), b.get("category_group")
    if ga and ga == gb:
        return 0.5
    if ga == "other" or gb == "other":
        return 0.25
    return None


def location_score(a, b):
    la, lb = a.get("location"), b.get("location")
    if not la or not lb:
        return None, None
    if la.get("id") == lb.get("id"):
        return 1.0, 0.0
    if None not in (la.get("x"), la.get("y"), lb.get("x"), lb.get("y")):
        d = math.hypot(la["x"] - lb["x"], la["y"] - lb["y"])
        return math.exp(-d / 250.0), d
    if la.get("block") and la.get("block") == lb.get("block"):
        return 0.7, None
    return 0.25, None


def _as_date(v):
    return v.date() if isinstance(v, datetime) else v


def date_score(a, b):
    da, db = _as_date(a.get("date")), _as_date(b.get("date"))
    if not da or not db:
        return None, None
    lost, found = (da, db) if a.get("type") == "lost" else (db, da)
    days = abs((da - db).days)
    score = math.exp(-days / 10.0)
    if (lost - found).days > 1:  # found well before it was lost: implausible
        score *= 0.5
    ta, tb = a.get("time"), b.get("time")
    if days == 0 and ta and tb:
        hours = abs((ta.hour * 60 + ta.minute) - (tb.hour * 60 + tb.minute)) / 60.0
        score *= 0.8 + 0.2 * math.exp(-hours / 6.0)
    return score, days


def normalise_weights(weights):
    w = {k: max(0.0, float(weights.get(k, DEFAULT_WEIGHTS[k]))) for k in DEFAULT_WEIGHTS}
    return w


@dataclass
class MatchResult:
    score: float
    components: dict = field(default_factory=dict)
    explanation: str = ""


def compare(a, b, text_sim, weights=None, visual=None):
    """Compare two report feature dicts. Returns None if they cannot be a match (same type,
    same report, incompatible category), else a MatchResult with score in 0..1."""
    if a.get("id") is not None and a.get("id") == b.get("id"):
        return None
    if a.get("type") == b.get("type"):
        return None
    cat = category_score(a, b)
    if cat is None:
        return None
    loc, dist = location_score(a, b)
    dt, days = date_score(a, b)
    raw = {"category": cat, "text": text_sim, "location": loc, "date": dt, "visual": visual}
    w = normalise_weights(weights or DEFAULT_WEIGHTS)
    avail = {k: v for k, v in raw.items() if v is not None and w[k] > 0}
    total = sum(w[k] for k in avail)
    if total <= 0:
        return None
    score = sum(w[k] * avail[k] for k in avail) / total
    components = {k: {"score": round(raw[k], 3) if raw[k] is not None else None,
                      "weight_used": round(w[k] / total, 3) if k in avail else 0.0} for k in raw}
    reasons = []
    reasons.append("Same category" if cat == 1.0 else "Related category")
    if text_sim is not None and text_sim >= 0.15:
        kws = shared_keywords(a.get("text"), b.get("text"))
        reasons.append("descriptions share: " + ", ".join(kws) if kws else "descriptions are similar")
    if loc is not None:
        if dist == 0.0:
            reasons.append("same campus location")
        elif dist is not None:
            reasons.append(f"locations about {int(round(dist, -1))} m apart")
        elif loc >= 0.7:
            reasons.append("same block")
    if days is not None:
        reasons.append("same day" if days == 0 else f"dates {days} day{'s' if days != 1 else ''} apart")
    if visual is not None and visual >= 0.5:
        reasons.append("photos look alike")
    explanation = "; ".join(reasons).capitalize() + "."
    return MatchResult(round(score, 4), components, explanation)
