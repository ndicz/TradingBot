"""Lightweight keyword-based sentiment scoring for news headlines.

No external NLP/API dependency — just a curated positive/negative keyword
list matched against headline titles. Coarse by design: good enough to
nudge a technical signal, not a substitute for reading the news.
"""

from __future__ import annotations

import re

POSITIVE_WORDS = {
    "surge", "surges", "surged", "rally", "rallies", "soar", "soars", "soared",
    "jump", "jumps", "gain", "gains", "bullish", "breakout", "upgrade", "upgraded",
    "outperform", "beat", "beats", "record high", "all-time high", "buy rating",
    "strong buy", "approval", "approved", "partnership", "expansion", "profit",
    "profits", "growth", "rebound", "recovery", "boost", "boosts", "upbeat",
    "breakthrough", "milestone", "adoption", "inflow", "inflows",
}

NEGATIVE_WORDS = {
    "crash", "crashes", "plunge", "plunges", "plunged", "drop", "drops", "dropped",
    "sell-off", "selloff", "bearish", "downgrade", "downgraded", "underperform",
    "miss", "misses", "missed", "fraud", "lawsuit", "hack", "hacked", "hacks",
    "ban", "banned", "probe", "investigation", "fine", "fined", "recession",
    "decline", "declines", "fear", "fears", "fall", "falls", "tumble", "tumbles",
    "warning", "cut", "cuts", "layoff", "layoffs", "bankruptcy", "default",
    "scandal", "outflow", "outflows", "slump", "slumps",
}

_word_re = re.compile(r"[a-z][a-z\-]*[a-z]|[a-z]")


def _tokens(text: str) -> set[str]:
    return set(_word_re.findall(text.lower()))


def score_headlines(items: list[dict]) -> dict:
    """Aggregate sentiment across a list of {"title": ...} news items."""
    pos_hits: list[str] = []
    neg_hits: list[str] = []

    for item in items:
        title = (item.get("title") or "").lower()
        words = _tokens(title)
        for kw in POSITIVE_WORDS:
            matched = (kw in title) if " " in kw else (kw in words)
            if matched:
                pos_hits.append(kw)
        for kw in NEGATIVE_WORDS:
            matched = (kw in title) if " " in kw else (kw in words)
            if matched:
                neg_hits.append(kw)

    score = len(pos_hits) - len(neg_hits)
    if score > 0:
        sentiment = "positive"
    elif score < 0:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        "sentiment": sentiment,
        "score": score,
        "positive_hits": sorted(set(pos_hits)),
        "negative_hits": sorted(set(neg_hits)),
    }


_TECH_SIGNAL_SCORE = {"SELL": -2, "WEAK SELL": -1, "HOLD": 0, "WEAK BUY": 1, "BUY": 2}
_SENTIMENT_SCORE = {"negative": -1, "neutral": 0, "positive": 1}


def combine_signal(technical_signal: str, sentiment: str) -> str:
    """Blend the technical (EMA/RSI/MACD/BB) signal with headline sentiment
    into a single suggested action. Sentiment can only nudge the signal by
    one step — it never flips a strong technical BUY into a SELL, etc."""
    total = _TECH_SIGNAL_SCORE.get(technical_signal, 0) + _SENTIMENT_SCORE.get(sentiment, 0)
    if total >= 2:
        return "BUY"
    if total >= 1:
        return "WEAK BUY"
    if total <= -2:
        return "SELL"
    if total <= -1:
        return "WEAK SELL"
    return "HOLD"
