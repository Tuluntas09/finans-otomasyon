"""
Günlük snapshot job — her sabah 9:00 TR (06:00 UTC) çalışacak.

Yaptığı işler:
  1. Watchlist'teki tüm semboller için quote + metrics + news + recommendation çek
  2. Analiz motorunu koştur (hisseye 6 boyut, emtiaya 4 boyut)
  3. SQLite'a snapshot olarak yaz
  4. Skor değişimi/verdict değişimi varsa alert üret
  5. Run log'a girdi ekle

Manuel çalıştırma:
    python -m jobs.daily_snapshot

GitHub Actions cron:
    .github/workflows/daily-snapshot.yml içinde tanımlı (06:00 UTC daily).
"""
from __future__ import annotations

import json
import logging
import sys
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from config.settings import all_symbols, display_name, load_watchlist
from core import database as db
from core.analyzer import analyze_commodity, analyze_stock, AnalysisResult
from core.finnhub_client import (
    FinnhubError, InvalidApiKey, NoApiKey, NotFound,
    RateLimited, get_client,
)
from core.news_analyzer import aggregate, enrich

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("daily_snapshot")


def _result_to_payload(res: AnalysisResult) -> dict[str, Any]:
    """AnalysisResult'ı JSON-uyumlu sözlüğe çevir (raw_payload için)."""
    return {
        "summary":         res.summary,
        "verdict_label":   res.verdict_label,
        "verdict_color":   res.verdict_color,
        "pros":            res.pros,
        "cons":            res.cons,
        "dimensions":      [asdict(d) for d in res.dimensions],
        "technical":       res.technical,
        "returns":         res.technical.get("returns", {}),
        "raw_metrics":     res.raw_metrics,
        "market_cap":      res.raw_metrics.get("marketCapitalization"),
    }


def _maybe_alert(symbol: str, new_score: int | None, new_verdict: str,
                 previous: dict[str, Any] | None) -> None:
    """Skor sıçraması veya verdict değişimi olunca alert yaz."""
    if not previous:
        return
    old_score   = previous.get("overall_score")
    old_verdict = previous.get("verdict")

    if (old_score is not None and new_score is not None
            and abs(new_score - old_score) >= 10):
        direction = "yükseldi" if new_score > old_score else "düştü"
        db.save_alert(
            symbol=symbol, kind="score_jump",
            severity="warning" if abs(new_score - old_score) >= 15 else "info",
            message=f"Skor {old_score} → {new_score} ({direction}).",
            payload={"old": old_score, "new": new_score},
        )

    if old_verdict and old_verdict != new_verdict and new_verdict != "VERİ YOK":
        sev = "critical" if (
            (old_verdict in {"AL", "GÜÇLÜ AL"} and new_verdict in {"SAT", "GÜÇLÜ SAT"})
            or (old_verdict in {"SAT", "GÜÇLÜ SAT"} and new_verdict in {"AL", "GÜÇLÜ AL"})
        ) else "warning"
        db.save_alert(
            symbol=symbol, kind="verdict_change", severity=sev,
            message=f"Karar değişti: {old_verdict} → {new_verdict}.",
            payload={"old": old_verdict, "new": new_verdict},
        )


def _process_symbol(client, sym: str, asset_kind: str, name: str) -> tuple[bool, int]:
    """
    Tek sembolü işle. (success, news_count_added) döndürür.
    """
    try:
        quote = client.quote(sym)
    except NotFound:
        log.warning("%s: quote bulunamadı, atlanıyor", sym)
        return False, 0

    try:
        metrics = client.metrics(sym)
    except FinnhubError as e:
        log.warning("%s: metrics alınamadı (%s)", sym, e)
        metrics = {}

    try:
        candles = client.candles(sym, resolution="D", days_back=365)
    except FinnhubError as e:
        log.warning("%s: candles alınamadı (%s)", sym, e)
        candles = {}

    # Haberler — sentiment'a göre enrich et, DB'ye yaz
    news_added = 0
    try:
        raw_news = client.news(sym, days_back=14)
        enriched = enrich(raw_news)
        news_added = db.save_news(sym, enriched)
        news_agg = aggregate(enriched)
        avg_sent = news_agg.get("avg_sentiment")
    except FinnhubError as e:
        log.warning("%s: haberler alınamadı (%s)", sym, e)
        avg_sent = None

    # Analiz
    if asset_kind == "commodity":
        result = analyze_commodity(sym, name, quote, metrics, candles, avg_sent)
    else:
        try:
            recommendations = client.recommendation(sym)
        except FinnhubError as e:
            log.warning("%s: recommendation alınamadı (%s)", sym, e)
            recommendations = []
        result = analyze_stock(sym, name, quote, metrics, recommendations,
                               candles, avg_sent)

    # Önceki snapshot
    prev = db.latest_snapshot(sym)
    payload = _result_to_payload(result)
    payload["quote"] = quote
    db.save_snapshot(
        symbol=sym, asset_type=asset_kind,
        price=quote.get("c"),
        change_pct=quote.get("dp"),
        overall_score=result.overall_score,
        verdict=result.verdict_label,
        payload=payload,
        dim_scores={d.key: d.score for d in result.dimensions},
    )
    _maybe_alert(sym, result.overall_score, result.verdict_label, prev)
    log.info("%s ✓ skor=%s verdict=%s yeni_haber=%d",
             sym, result.overall_score, result.verdict_label, news_added)
    return True, news_added


def run_snapshot() -> dict[str, Any]:
    """Tüm watchlist için snapshot çalıştır. Özet sözlük döndürür."""
    db.init_db()
    run_id = db.log_run_start("daily_snapshot")
    started = datetime.now(timezone.utc)

    wl = load_watchlist()
    items: list[tuple[str, str, str]] = (
        [(s["symbol"], s.get("name", s["symbol"]), "stock")        for s in wl["stocks"]] +
        [(s["symbol"], s.get("name", s["symbol"]), "commodity")   for s in wl["commodities"]]
    )

    summary = {"total": len(items), "ok": 0, "failed": 0,
               "news_added": 0, "errors": []}

    try:
        client = get_client()
    except NoApiKey as e:
        db.log_run_end(run_id, "failed", str(e))
        raise

    for sym, name, kind in items:
        try:
            ok, added = _process_symbol(client, sym, kind, name)
            if ok:
                summary["ok"] += 1
                summary["news_added"] += added
            else:
                summary["failed"] += 1
        except RateLimited as e:
            summary["failed"] += 1
            summary["errors"].append(f"{sym}: rate-limited ({e})")
            log.error("%s: rate limit — kalan semboller atlanıyor", sym)
            break
        except InvalidApiKey as e:
            summary["failed"] += 1
            summary["errors"].append(f"{sym}: invalid key")
            db.log_run_end(run_id, "failed", "Invalid API key")
            raise
        except Exception as e:
            summary["failed"] += 1
            summary["errors"].append(f"{sym}: {e}")
            log.exception("%s işlenirken hata", sym)

    duration = (datetime.now(timezone.utc) - started).total_seconds()
    status = (
        "ok" if summary["failed"] == 0 else
        "partial" if summary["ok"] > 0 else "failed"
    )
    detail = (
        f"{summary['ok']}/{summary['total']} ok, "
        f"{summary['news_added']} yeni haber, "
        f"{duration:.1f}s"
    )
    db.log_run_end(run_id, status, detail)
    log.info("Bitti: %s", detail)
    return summary


def main() -> int:
    try:
        summary = run_snapshot()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary["failed"] == 0 else 1
    except NoApiKey:
        print("FINNHUB_API_KEY tanımlı değil. .env dosyasına ekle.",
              file=sys.stderr)
        return 2
    except InvalidApiKey as e:
        print(f"Geçersiz API anahtarı: {e}", file=sys.stderr)
        return 2
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
