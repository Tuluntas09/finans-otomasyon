"""
Yatırım önerisi motoru.

Tek bir hisse için analiz yapmak yeterli değil — *tüm watchlist* üzerinde
karşılaştırmalı bir öneri listesi üretmek gerekiyor. Kullanıcının asıl
sorusu "şu an neye yatırım yapayım" ise cevap aşağıdakilerin bileşkesi:

  1. Genel analiz skoru (analyzer.py)
  2. Son 30 günde skor trendi (yukarı/aşağı/yatay)
  3. Haber sentiment'i (son 14 gün)
  4. Momentum (3 ay getirisi)

Final öneri skoru = ağırlıklı kombinasyon. Üst 3 sıra "Bugün ön plana çıkan"
fırsat olarak işaretlenir.

Önemli: Bu bir araştırma yardımcısıdır, yatırım tavsiyesi değildir.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any

from core import database as db


# Final öneri skoru için ağırlıklar
REC_WEIGHTS = {
    "analysis":  0.50,   # 6 boyutlu skor (en önemli)
    "trend":     0.20,   # son 30 günde skor değişimi
    "sentiment": 0.15,   # son 14 gün haber sentiment'i
    "momentum":  0.15,   # 3 ay fiyat getirisi
}


@dataclass
class Recommendation:
    symbol: str
    name: str
    asset_type: str
    final_score: int                # 0-100
    action: str                     # "AL" / "BİRİKTİR" / "TUT" / "AZALT" / "SAT"
    action_color: str
    rationale: list[str]            # neden bu skor (3-4 madde)
    components: dict[str, float | int | None]


def _score_trend(score_history: list[dict[str, Any]]) -> tuple[int | None, float | None]:
    """
    Son 30 günde 'overall_score' eğimi.
    Dönüş: (eğim_skoru_0_100, gerçek_eğim_puan/gün).
    """
    if not score_history or len(score_history) < 2:
        return None, None
    # Sadece dimension="overall" diye kayıt tutmuyoruz; bunun yerine snapshot'ın
    # overall_score sütununu kullanacağız (recommend_all bunu sağlıyor).
    overalls = [(i, r["overall_score"]) for i, r in enumerate(score_history)
                if r.get("overall_score") is not None]
    if len(overalls) < 2:
        return None, None
    xs = [x for x, _ in overalls]
    ys = [y for _, y in overalls]
    # Basit lineer eğim
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num   = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    denom = sum((xs[i] - mean_x) ** 2 for i in range(n)) or 1
    slope = num / denom  # puan/snapshot

    # Eğimi 0-100 skoruna çevir:
    #   slope >= +0.5/gün → 92,   +0.2 → 74,   ±0.1 → 55,   -0.2 → 38,   <= -0.5 → 18
    sc = (
        92 if slope >=  0.5 else
        74 if slope >=  0.2 else
        55 if slope >= -0.1 else
        38 if slope >= -0.3 else 18
    )
    return sc, slope


def _sentiment_to_score(avg_sentiment: float | None) -> int | None:
    if avg_sentiment is None:
        return None
    return round((avg_sentiment + 1) * 50)


def _momentum_score(m3_return: float | None) -> int | None:
    if m3_return is None:
        return None
    return (
        92 if m3_return >= 15 else
        74 if m3_return >= 5  else
        55 if m3_return >= -5 else
        38 if m3_return >= -15 else 18
    )


def _action_from_score(sc: int) -> tuple[str, str]:
    if sc >= 75: return ("AL",       "#1f9d57")
    if sc >= 60: return ("BİRİKTİR", "#2ecc71")
    if sc >= 45: return ("TUT",      "#f5b942")
    if sc >= 32: return ("AZALT",    "#ff8a5c")
    return ("SAT", "#ff5c6c")


def recommend(
    symbol: str,
    name: str,
    asset_type: str,
    analysis_overall: int | None,
    analysis_history: list[dict[str, Any]],
    avg_sentiment: float | None,
    m3_return: float | None,
) -> Recommendation:
    """Tek sembol için öneri üret."""
    trend_score, slope = _score_trend(analysis_history)
    sent_score = _sentiment_to_score(avg_sentiment)
    mom_score  = _momentum_score(m3_return)

    components = {
        "analysis":  analysis_overall,
        "trend":     trend_score,
        "sentiment": sent_score,
        "momentum":  mom_score,
    }

    # Ağırlıklı kombinasyon — eksik boyutları yok say
    parts = [(REC_WEIGHTS[k], v) for k, v in components.items() if v is not None]
    if not parts:
        final = 0
    else:
        total_w = sum(w for w, _ in parts)
        final = round(sum(w * v for w, v in parts) / total_w)
    final = max(0, min(100, final))
    action, color = _action_from_score(final)

    rationale: list[str] = []
    if analysis_overall is not None:
        rationale.append(f"Temel analiz skoru: {analysis_overall}/100.")
    if trend_score is not None and slope is not None:
        if slope > 0.2:
            rationale.append(f"Skor son dönemde yükseliyor (~{slope:+.2f} puan/snapshot).")
        elif slope < -0.2:
            rationale.append(f"Skor son dönemde düşüyor (~{slope:+.2f} puan/snapshot).")
        else:
            rationale.append("Skor son dönemde yatay seyrediyor.")
    if avg_sentiment is not None:
        if avg_sentiment >= 0.1:
            rationale.append(f"Son 14 gün haberleri pozitif ({avg_sentiment:+.2f}).")
        elif avg_sentiment <= -0.1:
            rationale.append(f"Son 14 gün haberleri negatif ({avg_sentiment:+.2f}).")
        else:
            rationale.append(f"Haberler nötr ({avg_sentiment:+.2f}).")
    if m3_return is not None:
        rationale.append(f"3 aylık fiyat getirisi: {m3_return:+.1f}%.")

    return Recommendation(
        symbol=symbol, name=name, asset_type=asset_type,
        final_score=final, action=action, action_color=color,
        rationale=rationale, components=components,
    )


def recommend_all(symbols: list[tuple[str, str, str]]) -> list[Recommendation]:
    """
    Watchlist'in tamamı için sıralı öneri listesi.
    symbols: [(symbol, name, asset_type), ...]
    """
    recs: list[Recommendation] = []
    for sym, name, atype in symbols:
        snap = db.latest_snapshot(sym)
        if not snap:
            continue
        history = db.snapshot_history(sym, days=30)
        avg_sent = db.avg_sentiment(sym, days=14)
        # 3 ay getirisini DB'de tutmuyoruz; raw_payload içinden çek
        m3_return: float | None = None
        try:
            import json
            payload = json.loads(snap.get("raw_payload") or "{}")
            m3_return = payload.get("returns", {}).get("m3")
        except Exception:
            pass
        recs.append(recommend(
            sym, name, atype,
            analysis_overall=snap.get("overall_score"),
            analysis_history=history,
            avg_sentiment=avg_sent,
            m3_return=m3_return,
        ))
    recs.sort(key=lambda r: r.final_score, reverse=True)
    return recs


def diversification_warning(top_picks: list[Recommendation]) -> str | None:
    """İlk 3 öneri aynı sektörden ise uyarı üret."""
    # Burada sektör bilgisini bilmiyoruz (watchlist'ten getirilebilir),
    # asset_type seviyesinde basit uyarı veriyoruz.
    if len(top_picks) < 3:
        return None
    types = {p.asset_type for p in top_picks[:3]}
    if len(types) == 1 and "stock" in types:
        return ("⚠️ İlk 3 öneri de hisse senedi — emtia eklemek "
                "portföy çeşitlendirmesi için faydalı olabilir.")
    return None
