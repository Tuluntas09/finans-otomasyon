"""
Genel Bakış — design pages-main.jsx OverviewPage birebir port.

Düzen:
  page-head (başlık + meta)
  KPI strip — 5 sütun (Ort. Skor / Günlük Ort. / AL / TUT / SAT+AZALT)
  "Bugün Öne Çıkanlar" panel — 3 hl-card grid (final skoru en yüksek 3)
  2 sütun: Watchlist tablo (2.3fr) + Son Uyarılar (1fr)
  CSV export butonu
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone

import streamlit as st

from config.settings import asset_type, display_name, load_watchlist
from core import database as db
from core.price_history import get_close_prices
from core.recommender import recommend_all
from ui.components import (
    PALETTE, chg_badge, decision_badge, fmt_chg_class, fmt_chg_str, fmt_price,
    icon, kind_badge, kpi, page_head, panel, panel_close, panel_open,
    score_bar, score_color, sent_chip, spark_svg,
)


def _spark_prices(symbol: str, days: int = 90) -> list[float]:
    """
    Sparkline için fiyat listesi döndürür.
    Önce yfinance (gerçek tarihsel veri) dener; yeterli nokta yoksa
    DB snapshot geçmişine düşer.
    """
    prices = get_close_prices(symbol, days=days)
    if len(prices) >= 5:
        return prices
    # Fallback: DB snapshot'ları (günlük cron verisi)
    hist = db.snapshot_history(symbol, days=days)
    db_prices = [h["price"] for h in hist if h.get("price")]
    return db_prices if len(db_prices) >= 2 else prices


def _build_csv(symbols: list[str], snapshots: dict) -> bytes:
    """Watchlist verilerini CSV byte dizisine çevirir (Excel-uyumlu UTF-8 BOM)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "Sembol", "İsim", "Tür", "Fiyat (USD)", "Gün Değ %",
        "3A Momentum %", "Skor (/100)", "Karar", "Sentiment (14g)",
    ])
    for sym in symbols:
        snap = snapshots.get(sym) or {}
        name = display_name(sym)
        atype = asset_type(sym)
        price = snap.get("price", "")
        day   = snap.get("change_pct", "")
        try:
            payload = json.loads(snap.get("raw_payload") or "{}")
            m3 = (payload.get("returns") or {}).get("m3", "")
        except Exception:
            m3 = ""
        score   = snap.get("overall_score", "")
        verdict = snap.get("verdict", "")
        sent    = db.avg_sentiment(sym, days=14)
        sent_str = f"{sent:.2f}" if sent is not None else ""
        w.writerow([sym, name, atype, price, day, m3, score, verdict, sent_str])
    return buf.getvalue().encode("utf-8-sig")   # BOM → Excel Türkçe karakter uyumu


def render(symbols: list[str]) -> None:
    snapshots = db.latest_for_all(symbols)
    last_run = db.last_run("daily_snapshot")

    # ────────────────────── page-head ──────────────────────
    if last_run and last_run.get("finished_at"):
        try:
            dt = datetime.fromisoformat(last_run["finished_at"])
            meta = f"Canlı · son güncelleme {dt.strftime('%Y-%m-%d %H:%M')}"
        except ValueError:
            meta = "Canlı"
    else:
        meta = "Henüz veri yok"

    st.markdown(
        "<div class='page'>" + page_head(
            "Genel Bakış",
            sub="Watchlist günlük durumu ve yatırım sinyalleri",
            meta=meta, meta_status="ok" if last_run else "warn",
        ),
        unsafe_allow_html=True,
    )

    if not snapshots:
        st.markdown(
            panel(
                "Veri Yok",
                f"<div class='muted'>Sol menüden <b>Şimdi Çalıştır</b>'a basarak "
                f"ilk snapshot'u al.</div>",
                ico="overview",
            ) + "</div>",
            unsafe_allow_html=True,
        )
        return

    # ────────────────────── KPI strip ──────────────────────
    scores = [s["overall_score"] for s in snapshots.values()
              if s.get("overall_score") is not None]
    avg_score = round(sum(scores) / len(scores)) if scores else 0
    chgs = [s.get("change_pct") for s in snapshots.values()
            if s.get("change_pct") is not None]
    avg_chg = sum(chgs) / len(chgs) if chgs else 0
    chg_cls = fmt_chg_class(avg_chg)
    chg_col = PALETTE["pos"] if avg_chg >= 0 else PALETTE["neg"]

    cnt_al = sum(1 for s in snapshots.values() if s.get("verdict") == "AL")
    cnt_tut = sum(1 for s in snapshots.values() if s.get("verdict") == "TUT")
    cnt_sat = sum(1 for s in snapshots.values()
                  if s.get("verdict") in ("SAT", "AZALT", "GÜÇLÜ SAT"))

    kpi_html = (
        "<div class='grid' style='grid-template-columns:repeat(5,1fr); gap:10px; margin-bottom:16px;'>"
        + kpi("Ortalama Skor", str(avg_score), unit="/100",
              foot=f"<span class='muted'>{len(symbols)} sembol · watchlist</span>",
              color=score_color(avg_score), accent=True)
        + kpi("Günlük Ort. Değişim",
              ("+" if avg_chg >= 0 else "") + f"{avg_chg:.2f}", unit="%",
              foot=f"<span class='chg {chg_cls}'>"
                   f"{'▲' if avg_chg >= 0 else '▼'} bugün</span>",
              color=chg_col)
        + kpi("AL Sinyali", str(cnt_al),
              foot="<span class='muted'>güçlü pozisyon</span>",
              color=PALETTE["d_al"])
        + kpi("TUT Sinyali", str(cnt_tut),
              foot="<span class='muted'>nötr / bekle</span>",
              color=PALETTE["d_tut"])
        + kpi("SAT / AZALT", str(cnt_sat),
              foot="<span class='muted'>azaltılacak</span>",
              color=PALETTE["d_sat"])
        + "</div>"
    )
    st.markdown(kpi_html, unsafe_allow_html=True)

    # ────────────────────── Bugün öne çıkanlar (Top-3) ──────────────────────
    wl = load_watchlist()
    meta_map = {s["symbol"]: (s.get("name", s["symbol"]), "stock")
                for s in wl["stocks"]}
    meta_map.update({s["symbol"]: (s.get("name", s["symbol"]), "commodity")
                     for s in wl["commodities"]})
    triples = [(sym, *meta_map[sym]) for sym in symbols if sym in meta_map]
    recs = recommend_all(triples)
    top3 = recs[:3]

    if top3:
        cards_html = ""
        for i, r in enumerate(top3):
            snap = snapshots.get(r.symbol, {})
            day = snap.get("change_pct")
            day_cls = fmt_chg_class(day)
            day_str = fmt_chg_str(day)
            arrow = "▲ " if (day or 0) > 0.01 else ("▼ " if (day or 0) < -0.01 else "")
            kind = "stock" if r.asset_type == "stock" else "etf"
            score_col = score_color(r.final_score)

            # Sparkline: yfinance öncelikli gerçek 90g kapanış, accent mavi
            prices = _spark_prices(r.symbol, days=90)
            spark = spark_svg(prices, color=PALETTE["accent"], w=100, h=32) if len(prices) >= 2 else ""

            price_str = fmt_price(snap.get("price"))
            cards_html += (
                f"<div class='hl-card' onclick='window.parent.postMessage(\"detail:{r.symbol}\",\"*\")'>"
                # .hl-ticker — "#1 — TICKER" accent rengi
                f"<div style='font-family:var(--f-mono); font-size:13px; font-weight:700; "
                f"color:var(--accent); margin-bottom:6px;'>#{i+1} — {r.symbol}</div>"
                # Fiyat — büyük
                f"<div style='font-family:var(--f-mono); font-size:20px; font-weight:700; "
                f"color:var(--tx-hi); margin-bottom:10px;'>{price_str}</div>"
                # Mini sparkline
                f"<div style='margin:10px 0;'>{spark}</div>"
                # Footer: gün değişim | skor
                f"<div style='display:flex; justify-content:space-between; align-items:center; "
                f"padding-top:10px; border-top:1px solid var(--line); font-size:11px;'>"
                f"<span class='chg {day_cls}'>{arrow}{day_str}</span>"
                f"<span style='color:var(--accent); font-family:var(--f-mono); font-weight:600;'>"
                f"{r.final_score}/100</span>"
                f"</div>"
                f"</div>"
            )
        st.markdown(
            f"<div class='panel' style='margin-bottom:8px;'>"
            f"<div class='panel-head'>"
            f"<div class='panel-title'><span class='ico'>{icon('flame')}</span>"
            f"Bugün Öne Çıkanlar</div>"
            f"<span class='panel-note'>en yüksek final skor</span>"
            f"</div>"
            f"<div style='padding:16px; display:grid; "
            f"grid-template-columns:repeat(3,1fr); gap:14px;'>{cards_html}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # ── Kart altı navigasyon butonları ──────────────────────────
        nav_cols = st.columns(len(top3))
        for nav_col, r in zip(nav_cols, top3):
            with nav_col:
                if st.button(
                    f"↗  {r.symbol} — Detaya Git",
                    key=f"hl_nav_{r.symbol}",
                    use_container_width=True,
                ):
                    st.session_state["nav_idx"] = 1          # "Sembol Detayı"
                    st.session_state["detail_symbol"] = r.symbol
                    st.rerun()
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ────────────────────── Watchlist + Uyarılar (saf HTML grid) ──────────────────────
    # st.columns yerine HTML grid — overflow:auto tablo scroll'u çalışır, yükseklik senkron sorunu yok

    # Watchlist satırları
    rows_html = ""
    sorted_symbols = sorted(
        symbols,
        key=lambda s: (snapshots.get(s, {}).get("overall_score") or -1),
        reverse=True,
    )
    for sym in sorted_symbols:
        snap = snapshots.get(sym)
        name = display_name(sym)
        atype = asset_type(sym)
        kind = "stock" if atype == "stock" else "etf"

        if not snap:
            rows_html += (
                f"<tr>"
                f"<td><span class='tk'>{sym}</span> {kind_badge(kind)} "
                f"<span class='nm'>{name[:20]}</span></td>"
                f"<td colspan='7' class='muted'>veri yok</td>"
                f"</tr>"
            )
            continue

        price = snap.get("price")
        day = snap.get("change_pct")
        score = snap.get("overall_score")
        verdict = snap.get("verdict") or "—"
        sent = db.avg_sentiment(sym, days=14)
        try:
            payload = json.loads(snap.get("raw_payload") or "{}")
            m3 = (payload.get("returns") or {}).get("m3")
        except Exception:
            m3 = None

        m3_cls = fmt_chg_class(m3)
        m3_str = fmt_chg_str(m3)

        # 90 günlük sparkline: yfinance öncelikli
        prices_hist = _spark_prices(sym, days=90)
        spark_col = PALETTE["pos"] if (day or 0) >= 0 else PALETTE["neg"]
        spark = (spark_svg(prices_hist, color=spark_col, w=80, h=26)
                 if len(prices_hist) >= 2
                 else f"<span style='color:var(--tx-faint); font-size:10px;'>—</span>")

        rows_html += (
            f"<tr>"
            f"<td>"
            f"<div style='display:flex; align-items:center; gap:7px;'>"
            f"<span class='tk'>{sym}</span>{kind_badge(kind)}"
            f"<span class='nm' style='overflow:hidden; text-overflow:ellipsis; "
            f"white-space:nowrap; max-width:120px;'>{name}</span>"
            f"</div>"
            f"</td>"
            f"<td class='r mono hi'>{fmt_price(price)}</td>"
            f"<td class='r'>{chg_badge(day)}</td>"
            f"<td style='padding:4px 10px;'>{spark}</td>"
            f"<td style='min-width:110px;'>{score_bar(score)}</td>"
            f"<td>{decision_badge(verdict)}</td>"
            f"<td class='r'>{sent_chip(sent)}</td>"
            f"<td class='r'><span class='chg {m3_cls}'>{m3_str}</span></td>"
            f"</tr>"
        )

    watchlist_panel = (
        f"<div class='panel'>"
        f"<div class='panel-head'>"
        f"<div class='panel-title'><span class='ico'>{icon('list')}</span>Watchlist</div>"
        f"<span class='panel-note'>{len(symbols)} sembol · skora göre sıralı</span>"
        f"</div>"
        f"<div style='overflow-x:auto;'>"
        f"<table class='tbl'>"
        f"<thead><tr>"
        f"<th>Sembol</th>"
        f"<th class='r'>Fiyat</th>"
        f"<th class='r'>Gün %</th>"
        f"<th style='min-width:90px;'>90 Gün</th>"
        f"<th style='min-width:110px;'>Skor</th>"
        f"<th>Karar</th>"
        f"<th class='r'>Sent.</th>"
        f"<th class='r'>3A Mom.</th>"
        f"</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        f"</table>"
        f"</div>"
        f"</div>"
    )

    # Son Uyarılar paneli
    alerts = db.recent_alerts(limit=8)
    if alerts:
        alert_rows = ""
        for a in alerts:
            kind_dir = "up" if "yüksel" in (a.get("message") or "").lower() else "down"
            ic_color = PALETTE["pos"] if kind_dir == "up" else PALETTE["neg"]
            ic_name = "arrowUp" if kind_dir == "up" else "arrowDown"
            created = (a.get("created_at") or "")[:16].replace("T", " ")
            alert_rows += (
                f"<div style='display:flex; gap:10px; padding:10px 14px; "
                f"border-bottom:1px solid var(--line-faint);'>"
                f"<div style='width:26px; flex:0 0 26px; display:grid; "
                f"place-items:center; color:{ic_color};'>{icon(ic_name, w=14)}</div>"
                f"<div style='flex:1; min-width:0;'>"
                f"<div style='font-size:12px; color:var(--tx); line-height:1.35;'>"
                f"<b class='mono' style='color:var(--tx-hi); font-size:11.5px;'>{a['symbol']}</b>"
                f" · {a['message']}"
                f"</div>"
                f"<div style='font-size:10px; color:var(--tx-faint); font-family:var(--f-mono); margin-top:3px;'>"
                f"{created}</div>"
                f"</div></div>"
            )
        alerts_body = alert_rows
    else:
        alerts_body = "<div class='muted' style='padding:14px 16px; font-size:12.5px;'>Henüz uyarı yok</div>"

    alerts_panel = (
        f"<div class='panel'>"
        f"<div class='panel-head'>"
        f"<div class='panel-title'><span class='ico'>{icon('bell')}</span>Son Uyarılar</div>"
        f"</div>"
        f"{alerts_body}"
        f"</div>"
    )

    # İkisini tek HTML grid bloğu olarak render et
    st.markdown(
        f"<div style='display:grid; grid-template-columns:minmax(0,2.3fr) minmax(0,1fr); "
        f"gap:14px; align-items:start;'>"
        f"{watchlist_panel}"
        f"{alerts_panel}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── CSV Export ──────────────────────────────────────────────────
    csv_bytes = _build_csv(sorted_symbols, snapshots)
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    _, dl_col = st.columns([6, 1])
    with dl_col:
        st.download_button(
            label="⬇ CSV İndir",
            data=csv_bytes,
            file_name=f"watchlist_{today_str}.csv",
            mime="text/csv",
            key="wl_csv_dl",
            use_container_width=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)  # .page
