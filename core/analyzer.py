"""
Analiz motoru — saf fonksiyonel hesaplamalar.

İki paralel akış var:
  • analyze_stock(...)     → 6 boyutlu (değerleme, kârlılık, büyüme,
                              finansal sağlık, teknik, analist+haber)
  • analyze_commodity(...) → 4 boyutlu (teknik, haber, oynaklık, trend)

Her ikisi de aynı sözlük yapısını döner — UI tek format işliyor.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from config.settings import (
    COMMODITY_WEIGHTS,
    STOCK_WEIGHTS,
    THRESHOLDS,
    VERDICT_BANDS,
)


# ---------------------------------------------------------------- #
# Veri yapıları
# ---------------------------------------------------------------- #
@dataclass
class DimensionScore:
    key: str
    name: str
    weight: float
    score: int | None             # 0-100 ya da None (veri yok)
    quality: str                  # "iyi" / "orta" / "zayıf" / "yok"
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    symbol: str
    asset_type: str               # "stock" | "commodity"
    overall_score: int | None     # 0-100
    verdict_label: str            # "GÜÇLÜ AL" / "AL" / "TUT" / "SAT" / "GÜÇLÜ SAT"
    verdict_color: str
    summary: str
    dimensions: list[DimensionScore]
    pros: list[str]
    cons: list[str]
    technical: dict[str, Any] = field(default_factory=dict)  # 52H bandı, getiriler
    raw_metrics: dict[str, Any] = field(default_factory=dict)

    def dim_dict(self) -> dict[str, int | None]:
        return {d.key: d.score for d in self.dimensions}


# ---------------------------------------------------------------- #
# Yardımcılar
# ---------------------------------------------------------------- #
_DIM_LABELS = {
    "valuation":     "Değerleme",
    "profitability": "Kârlılık",
    "growth":        "Büyüme",
    "health":        "Finansal Sağlık",
    "technical":     "Teknik / Momentum",
    "analyst":       "Analist + Haber",
    "news":          "Haber Sentiment",
    "volatility":    "Oynaklık",
    "trend":         "Uzun Vadeli Trend",
}


def pick(metrics: dict[str, Any], keys: list[str]) -> float | None:
    """metrics içinden ilk dolu değeri döndür."""
    for k in keys:
        v = metrics.get(k)
        if v is not None and v != "" and isinstance(v, (int, float)) and not math.isnan(v):
            return float(v)
    return None


def score_by_thresholds(value: float | None, key: str) -> int | None:
    """Eşik tablosuna göre 0-100 skor üret. None → None."""
    if value is None:
        return None
    cfg = THRESHOLDS.get(key)
    if not cfg:
        return None
    direction, ts = cfg
    a, b, c, d = ts
    if direction == "up":
        if value >= a: return 92
        if value >= b: return 74
        if value >= c: return 55
        if value >= d: return 38
        return 18
    # "down"
    if value <= a: return 92
    if value <= b: return 74
    if value <= c: return 55
    if value <= d: return 38
    return 18


def quality_of(score: int | None) -> str:
    if score is None:    return "yok"
    if score >= 74:      return "iyi"
    if score >= 45:      return "orta"
    return "zayıf"


def verdict_of(score: int | None) -> tuple[str, str]:
    if score is None:
        return ("VERİ YOK", "#8a96ad")
    for thr, label, color in VERDICT_BANDS:
        if score >= thr:
            return (label, color)
    return VERDICT_BANDS[-1][1], VERDICT_BANDS[-1][2]


def weighted_avg(scores: list[tuple[float, int | None]]) -> int | None:
    """[(weight, score)] → ağırlıklı ortalama. Eksik boyutları yok say, kalanları yeniden normalize et."""
    avail = [(w, s) for w, s in scores if s is not None]
    if not avail:
        return None
    total_w = sum(w for w, _ in avail)
    if total_w <= 0:
        return None
    return round(sum(w * s for w, s in avail) / total_w)


# ---------------------------------------------------------------- #
# Teknik (her iki varlık tipi için ortak)
# ---------------------------------------------------------------- #
def technical_block(quote: dict[str, Any], metrics: dict[str, Any],
                    candles: dict[str, Any] | None) -> dict[str, Any]:
    """52 hafta bandı, getiriler, momentum skorları."""
    hi = pick(metrics, ["52WeekHigh"])
    lo = pick(metrics, ["52WeekLow"])
    price = quote.get("c")
    rng_pos = None
    if price is not None and hi and lo and hi > lo:
        rng_pos = (price - lo) / (hi - lo) * 100  # 0-100

    # Getiriler — mum verisi varsa hesapla
    returns: dict[str, float | None] = {"d5": None, "m1": None,
                                        "m3": None, "ytd": None, "y1": None}
    if candles and candles.get("c") and price:
        closes = candles["c"]
        times = candles.get("t", [])
        if closes:
            def ret_from(idx_from_end: int) -> float | None:
                if len(closes) > idx_from_end:
                    base = closes[-idx_from_end - 1]
                    if base and base > 0:
                        return (price / base - 1) * 100
                return None
            returns["d5"]  = ret_from(5)
            returns["m1"]  = ret_from(21)
            returns["m3"]  = ret_from(63)
            returns["y1"]  = ret_from(252)
            # YTD
            if times:
                year_start = datetime(datetime.now(timezone.utc).year, 1, 1,
                                       tzinfo=timezone.utc).timestamp()
                for t, p in zip(times, closes):
                    if t >= year_start and p:
                        returns["ytd"] = (price / p - 1) * 100
                        break

    # Skor: 52H konum + 3 ay getiri + beta
    pos_score = None if rng_pos is None else (
        92 if rng_pos >= 80 else
        74 if rng_pos >= 60 else
        55 if rng_pos >= 40 else
        38 if rng_pos >= 20 else 18
    )
    m3 = returns["m3"]
    mom_score = None if m3 is None else (
        92 if m3 >= 15 else
        74 if m3 >= 5  else
        55 if m3 >= -5 else
        38 if m3 >= -15 else 18
    )
    beta = pick(metrics, ["beta"])
    beta_score = score_by_thresholds(beta, "beta")

    parts = [s for s in (pos_score, mom_score, beta_score) if s is not None]
    tech_score = round(sum(parts) / len(parts)) if parts else None

    return {
        "hi": hi, "lo": lo, "price": price, "range_pos": rng_pos,
        "returns": returns, "beta": beta,
        "pos_score": pos_score, "mom_score": mom_score, "beta_score": beta_score,
        "score": tech_score,
    }


# ---------------------------------------------------------------- #
# Boyut hesaplayıcılar — stok
# ---------------------------------------------------------------- #
def _dim_valuation(m: dict[str, Any]) -> DimensionScore:
    pe  = pick(m, ["peTTM", "peBasicExclExtraTTM", "peExclExtraTTM"])
    pb  = pick(m, ["pbQuarterly", "pbAnnual"])
    ps  = pick(m, ["psTTM", "psAnnual"])
    parts = [
        score_by_thresholds(pe, "pe"),
        score_by_thresholds(pb, "pb"),
        score_by_thresholds(ps, "ps"),
    ]
    parts = [s for s in parts if s is not None]
    sc = round(sum(parts) / len(parts)) if parts else None
    return DimensionScore(
        "valuation", _DIM_LABELS["valuation"], STOCK_WEIGHTS["valuation"], sc,
        quality_of(sc), {"pe": pe, "pb": pb, "ps": ps},
    )


def _dim_profitability(m: dict[str, Any]) -> DimensionScore:
    roe = pick(m, ["roeTTM", "roeRfy"])
    roa = pick(m, ["roaTTM", "roaRfy"])
    nm  = pick(m, ["netProfitMarginTTM", "netProfitMarginAnnual"])
    gm  = pick(m, ["grossMarginTTM", "grossMarginAnnual"])
    parts = [
        score_by_thresholds(roe, "roe"),
        score_by_thresholds(roa, "roa"),
        score_by_thresholds(nm,  "net_margin"),
        score_by_thresholds(gm,  "gross_margin"),
    ]
    parts = [s for s in parts if s is not None]
    sc = round(sum(parts) / len(parts)) if parts else None
    return DimensionScore(
        "profitability", _DIM_LABELS["profitability"], STOCK_WEIGHTS["profitability"], sc,
        quality_of(sc), {"roe": roe, "roa": roa, "net_margin": nm, "gross_margin": gm},
    )


def _dim_growth(m: dict[str, Any]) -> DimensionScore:
    rev_ttm   = pick(m, ["revenueGrowthTTMYoy", "revenueGrowthQuarterlyYoy"])
    rev_5y    = pick(m, ["revenueGrowth5Y"])
    eps_ttm   = pick(m, ["epsGrowthTTMYoy", "epsGrowthQuarterlyYoy"])
    eps_5y    = pick(m, ["epsGrowth5Y"])
    parts = [
        score_by_thresholds(rev_ttm, "rev_growth"),
        score_by_thresholds(rev_5y,  "rev_growth"),
        score_by_thresholds(eps_ttm, "eps_growth"),
        score_by_thresholds(eps_5y,  "eps_growth"),
    ]
    parts = [s for s in parts if s is not None]
    sc = round(sum(parts) / len(parts)) if parts else None
    return DimensionScore(
        "growth", _DIM_LABELS["growth"], STOCK_WEIGHTS["growth"], sc,
        quality_of(sc),
        {"rev_ttm": rev_ttm, "rev_5y": rev_5y, "eps_ttm": eps_ttm, "eps_5y": eps_5y},
    )


def _dim_health(m: dict[str, Any]) -> DimensionScore:
    cr  = pick(m, ["currentRatioQuarterly", "currentRatioAnnual"])
    de  = pick(m, ["totalDebt/totalEquityQuarterly", "totalDebt/totalEquityAnnual"])
    parts = [
        score_by_thresholds(cr, "current_ratio"),
        score_by_thresholds(de, "debt_equity"),
    ]
    parts = [s for s in parts if s is not None]
    sc = round(sum(parts) / len(parts)) if parts else None
    return DimensionScore(
        "health", _DIM_LABELS["health"], STOCK_WEIGHTS["health"], sc,
        quality_of(sc), {"current_ratio": cr, "debt_equity": de},
    )


def _dim_technical(tech: dict[str, Any]) -> DimensionScore:
    return DimensionScore(
        "technical", _DIM_LABELS["technical"], STOCK_WEIGHTS["technical"],
        tech["score"], quality_of(tech["score"]),
        {k: tech[k] for k in ("range_pos", "returns", "beta", "pos_score", "mom_score")
         if k in tech},
    )


def _dim_analyst(rec: list[dict[str, Any]], news_sentiment: float | None) -> DimensionScore:
    """Analist konsensüsü (%70) + haber sentiment (%30) kombinasyonu."""
    rec_score: int | None = None
    rec_details: dict[str, Any] = {}
    if rec:
        r = rec[0]
        total = (r.get("strongBuy", 0) + r.get("buy", 0) + r.get("hold", 0)
                 + r.get("sell", 0) + r.get("strongSell", 0)) or 1
        weighted = (
            r.get("strongBuy", 0) * 100 + r.get("buy", 0) * 75 +
            r.get("hold", 0)      * 50 + r.get("sell", 0) * 25 +
            r.get("strongSell", 0) * 0
        ) / total
        rec_score = round(weighted)
        rec_details = {k: r.get(k, 0) for k in
                       ("strongBuy", "buy", "hold", "sell", "strongSell")}
        rec_details["period"] = r.get("period")

    news_score: int | None = None
    if news_sentiment is not None:
        # -1..+1 → 0..100 (lineer)
        news_score = round((news_sentiment + 1) * 50)

    parts: list[tuple[float, int]] = []
    if rec_score  is not None: parts.append((0.7, rec_score))
    if news_score is not None: parts.append((0.3, news_score))
    sc: int | None = None
    if parts:
        total_w = sum(w for w, _ in parts)
        sc = round(sum(w * s for w, s in parts) / total_w)

    return DimensionScore(
        "analyst", _DIM_LABELS["analyst"], STOCK_WEIGHTS["analyst"], sc,
        quality_of(sc),
        {"recommendation_score": rec_score, "news_score": news_score, **rec_details},
    )


# ---------------------------------------------------------------- #
# Boyut hesaplayıcılar — emtia
# ---------------------------------------------------------------- #
def _commodity_volatility(candles: dict[str, Any]) -> tuple[int | None, float | None]:
    """Son 60 günün kapanış std-sapması üzerinden oynaklık skoru."""
    if not candles or not candles.get("c"):
        return None, None
    closes = candles["c"][-60:]
    if len(closes) < 20:
        return None, None
    returns = [(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes)) if closes[i - 1]]
    if not returns:
        return None, None
    vol = statistics.stdev(returns) * math.sqrt(252) * 100  # yıllık % vol
    # Düşük vol → yüksek skor (daha güvenilir trend)
    sc = (
        92 if vol < 15 else
        74 if vol < 25 else
        55 if vol < 40 else
        38 if vol < 60 else 18
    )
    return sc, vol


def _commodity_trend(candles: dict[str, Any]) -> tuple[int | None, float | None]:
    """SMA50 vs SMA200 — altın çapraz / ölüm çaprazı."""
    if not candles or not candles.get("c"):
        return None, None
    closes = candles["c"]
    if len(closes) < 200:
        return None, None
    sma50  = sum(closes[-50:])  / 50
    sma200 = sum(closes[-200:]) / 200
    if sma200 == 0:
        return None, None
    diff_pct = (sma50 / sma200 - 1) * 100
    sc = (
        92 if diff_pct > 10 else
        74 if diff_pct > 3  else
        55 if diff_pct > -3 else
        38 if diff_pct > -10 else 18
    )
    return sc, diff_pct


# ---------------------------------------------------------------- #
# Özet metin
# ---------------------------------------------------------------- #
def _summary_text(name: str, overall: int | None, verdict: str,
                  dims: list[DimensionScore]) -> str:
    if overall is None:
        return f"{name} için yeterli veri toplanamadı."
    strong = [d.name for d in dims if d.score and d.score >= 74]
    weak   = [d.name for d in dims if d.score and d.score < 45]
    parts = [f"Genel skor {overall}/100 — **{verdict}**."]
    if strong:
        parts.append("Güçlü taraflar: " + ", ".join(strong) + ".")
    if weak:
        parts.append("Zayıf taraflar: " + ", ".join(weak) + ".")
    return " ".join(parts)


def _build_pros_cons(dims: list[DimensionScore],
                     news_sentiment: float | None) -> tuple[list[str], list[str]]:
    pros, cons = [], []
    for d in dims:
        if d.score is None:
            continue
        if d.score >= 74:
            pros.append(f"{d.name}: skor {d.score} — güçlü.")
        elif d.score < 45:
            cons.append(f"{d.name}: skor {d.score} — zayıf, dikkat.")
    if news_sentiment is not None:
        if news_sentiment >= 0.2:
            pros.append(f"Son 14 günde haber sentiment'i pozitif ({news_sentiment:+.2f}).")
        elif news_sentiment <= -0.2:
            cons.append(f"Son 14 günde haber sentiment'i negatif ({news_sentiment:+.2f}).")
    return pros, cons


# ---------------------------------------------------------------- #
# Public API
# ---------------------------------------------------------------- #
def analyze_stock(
    symbol: str,
    name: str,
    quote: dict[str, Any],
    metrics: dict[str, Any],
    recommendations: list[dict[str, Any]],
    candles: dict[str, Any] | None,
    news_sentiment: float | None,
) -> AnalysisResult:
    tech = technical_block(quote, metrics, candles)
    dims = [
        _dim_valuation(metrics),
        _dim_profitability(metrics),
        _dim_growth(metrics),
        _dim_health(metrics),
        _dim_technical(tech),
        _dim_analyst(recommendations, news_sentiment),
    ]
    overall = weighted_avg([(d.weight, d.score) for d in dims])
    label, color = verdict_of(overall)
    pros, cons = _build_pros_cons(dims, news_sentiment)
    return AnalysisResult(
        symbol=symbol, asset_type="stock",
        overall_score=overall, verdict_label=label, verdict_color=color,
        summary=_summary_text(name, overall, label, dims),
        dimensions=dims, pros=pros, cons=cons,
        technical=tech, raw_metrics=metrics,
    )


def analyze_commodity(
    symbol: str,
    name: str,
    quote: dict[str, Any],
    metrics: dict[str, Any],
    candles: dict[str, Any] | None,
    news_sentiment: float | None,
) -> AnalysisResult:
    tech = technical_block(quote, metrics, candles)
    vol_score, vol_value = _commodity_volatility(candles or {})
    trend_score, trend_value = _commodity_trend(candles or {})
    news_score = None
    if news_sentiment is not None:
        news_score = round((news_sentiment + 1) * 50)

    dims = [
        DimensionScore(
            "technical", _DIM_LABELS["technical"], COMMODITY_WEIGHTS["technical"],
            tech["score"], quality_of(tech["score"]),
            {k: tech[k] for k in ("range_pos", "returns")},
        ),
        DimensionScore(
            "news", _DIM_LABELS["news"], COMMODITY_WEIGHTS["news"],
            news_score, quality_of(news_score),
            {"avg_sentiment": news_sentiment},
        ),
        DimensionScore(
            "volatility", _DIM_LABELS["volatility"], COMMODITY_WEIGHTS["volatility"],
            vol_score, quality_of(vol_score),
            {"annual_vol_pct": vol_value},
        ),
        DimensionScore(
            "trend", _DIM_LABELS["trend"], COMMODITY_WEIGHTS["trend"],
            trend_score, quality_of(trend_score),
            {"sma50_vs_sma200_pct": trend_value},
        ),
    ]
    overall = weighted_avg([(d.weight, d.score) for d in dims])
    label, color = verdict_of(overall)
    pros, cons = _build_pros_cons(dims, news_sentiment)
    return AnalysisResult(
        symbol=symbol, asset_type="commodity",
        overall_score=overall, verdict_label=label, verdict_color=color,
        summary=_summary_text(name, overall, label, dims),
        dimensions=dims, pros=pros, cons=cons,
        technical=tech, raw_metrics=metrics,
    )
