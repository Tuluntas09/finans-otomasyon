"""
Haber analizi — sentiment skoru + kategori etiketleme.

Finnhub'tan gelen ham haber listesini alır, her habere VADER tabanlı
compound skor (-1..+1) ekler ve başlık anahtar kelimelerine bakarak
kategori atar (earnings, M&A, regulatory, ...).

VADER İngilizce için tasarlandı — Finnhub haberlerinin neredeyse tamamı
İngilizce olduğu için yeterli. Türkçe başlık gelirse skor 0 (nötr) olur,
bu da zaten doğru muhafazakâr davranış.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from config.settings import (
    NEWS_CATEGORIES,
    NEWS_MAX_PER_SYMBOL,
    SENTIMENT_BANDS,
)

log = logging.getLogger(__name__)
_ANALYZER = SentimentIntensityAnalyzer()


def sentiment_label(score: float | None) -> tuple[str, str]:
    """Compound skoru → ('Pozitif', '#2ecc71') gibi etiket+renk."""
    if score is None:
        return ("Veri yok", "#8a96ad")
    for thr, label, color in SENTIMENT_BANDS:
        if score >= thr:
            return (label, color)
    return SENTIMENT_BANDS[-1][1], SENTIMENT_BANDS[-1][2]


def categorize(headline: str) -> str:
    """Başlık anahtar kelimelerine göre kategori atar. İlk eşleşeni kullanır."""
    h = (headline or "").lower()
    for cat, keywords in NEWS_CATEGORIES.items():
        if any(kw in h for kw in keywords):
            return cat
    return "other"


def _score_text(text: str) -> float:
    """VADER compound skoru -1..+1."""
    if not text:
        return 0.0
    return _ANALYZER.polarity_scores(text)["compound"]


def enrich(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Finnhub haber listesini al, sentiment + kategori ekle.

    Finnhub haber formatı:
      { "category": "...", "datetime": 1700000000, "headline": "...",
        "id": 1234, "image": "...", "related": "AAPL",
        "source": "...", "summary": "...", "url": "..." }
    """
    out: list[dict[str, Any]] = []
    for n in items[:NEWS_MAX_PER_SYMBOL]:
        headline = n.get("headline") or ""
        summary  = n.get("summary")  or ""
        text     = f"{headline}. {summary}".strip()
        compound = _score_text(text)
        ts = n.get("datetime")
        published_iso = (
            datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")
            if isinstance(ts, (int, float)) and ts > 0 else None
        )
        out.append({
            "id":           n.get("id"),
            "headline":     headline,
            "summary":      summary[:500] if summary else "",
            "source":       n.get("source"),
            "url":          n.get("url"),
            "image":        n.get("image"),
            "published_at": published_iso,
            "sentiment":    round(compound, 3),
            "category":     categorize(headline),
        })
    return out


def aggregate(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Bir hisse için haber paketinin özet metrikleri."""
    if not items:
        return {
            "count": 0,
            "avg_sentiment": None,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "category_breakdown": {},
            "top_positive": None,
            "top_negative": None,
        }
    scored = [n for n in items if n.get("sentiment") is not None]
    avg = sum(n["sentiment"] for n in scored) / len(scored) if scored else None
    pos = sum(1 for n in scored if n["sentiment"] >= 0.05)
    neg = sum(1 for n in scored if n["sentiment"] <= -0.05)
    neu = len(scored) - pos - neg
    cats: dict[str, int] = {}
    for n in items:
        cats[n.get("category", "other")] = cats.get(n.get("category", "other"), 0) + 1
    top_pos = max(items, key=lambda x: x.get("sentiment", 0), default=None)
    top_neg = min(items, key=lambda x: x.get("sentiment", 0), default=None)
    return {
        "count": len(items),
        "avg_sentiment": round(avg, 3) if avg is not None else None,
        "positive_count": pos,
        "negative_count": neg,
        "neutral_count":  neu,
        "category_breakdown": cats,
        "top_positive": top_pos if top_pos and top_pos.get("sentiment", 0) > 0 else None,
        "top_negative": top_neg if top_neg and top_neg.get("sentiment", 0) < 0 else None,
    }


CATEGORY_LABELS = {
    "earnings":   "📊 Bilanço",
    "ma":         "🤝 Satın Alma/Birleşme",
    "product":    "🚀 Ürün/Lansman",
    "regulatory": "⚖️ Regülasyon",
    "analyst":    "🎯 Analist",
    "macro":      "🌐 Makro",
    "leadership": "👤 Yönetim",
    "tech":       "💻 Teknoloji",
    "other":      "📰 Diğer",
}
