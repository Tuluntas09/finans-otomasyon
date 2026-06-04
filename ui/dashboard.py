"""
Ana sayfa — watchlist tarayıcı.

Tüm semboller için son snapshot'ları gösterir; Top 3 öneri, sektör/varlık
dağılımı ve son uyarıların özetini içerir.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st

from config.settings import asset_type, display_name, load_watchlist
from core import database as db
from core.recommender import recommend_all, diversification_warning
from ui.components import (
    PALETTE, chg_badge, fmt_num, score_history_chart, verdict_badge,
)


def render(symbols: list[str]) -> None:
    st.markdown("## 📊 Genel Bakış")
    st.caption("Watchlist'teki tüm varlıkların son durumu ve bugünün öne çıkan fırsatları.")

    last_run = db.last_run("daily_snapshot")
    col_a, col_b, col_c, col_d = st.columns(4)
    snapshots = db.latest_for_all(symbols)
    col_a.metric("Takip edilen sembol", len(symbols))
    col_b.metric("Snapshot verisi olan", len(snapshots))
    if last_run and last_run.get("finished_at"):
        last_iso = last_run["finished_at"]
        try:
            dt = datetime.fromisoformat(last_iso)
            delta_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            col_c.metric("Son güncelleme", f"{delta_h:.1f} sa önce",
                         last_run.get("status", "?"))
        except ValueError:
            col_c.metric("Son güncelleme", last_iso[:10])
    else:
        col_c.metric("Son güncelleme", "—", "henüz çalışmadı")

    avg_score = None
    if snapshots:
        scores = [s["overall_score"] for s in snapshots.values()
                  if s.get("overall_score") is not None]
        if scores:
            avg_score = round(sum(scores) / len(scores))
    col_d.metric("Watchlist ortalama skoru", avg_score if avg_score is not None else "—")

    if not snapshots:
        st.info("Henüz veri yok. Sol menüden **'🔄 Veri Topla'** ile ilk snapshot'u "
                "başlat ya da `python -m jobs.daily_snapshot` komutunu çalıştır.")
        return

    # ------------------------------------------------------------ #
    # Bugünün öne çıkan 3 fırsatı
    # ------------------------------------------------------------ #
    st.markdown("### 🎯 Bugünün Öne Çıkan Fırsatları")
    wl = load_watchlist()
    symbol_meta = {s["symbol"]: (s.get("name", s["symbol"]), "stock")
                   for s in wl["stocks"]}
    symbol_meta.update({s["symbol"]: (s.get("name", s["symbol"]), "commodity")
                        for s in wl["commodities"]})
    triples = [(sym, *symbol_meta[sym]) for sym in symbols if sym in symbol_meta]
    recs = recommend_all(triples)
    top3 = recs[:3]

    if not top3:
        st.warning("Öneri üretmek için yeterli geçmiş veri yok (en az 2 snapshot).")
    else:
        cols = st.columns(3)
        for i, r in enumerate(top3):
            with cols[i]:
                st.markdown(f"""
                <div class='fcard' style='border-left: 4px solid {r.action_color};'>
                  <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <div>
                      <div style='font-size:18px; font-weight:800;'>{r.symbol}</div>
                      <div style='color:{PALETTE['muted']}; font-size:12px;'>{r.name}</div>
                    </div>
                    <div style='text-align:right;'>
                      <div style='font-size:28px; font-weight:800; color:{r.action_color};'>{r.final_score}</div>
                      <div style='font-size:11px; color:{PALETTE['muted']};'>FİNAL SKOR</div>
                    </div>
                  </div>
                  <div style='margin-top:10px;'>
                    <span class='badge' style='background:{r.action_color}22;color:{r.action_color};'>{r.action}</span>
                    <span class='pill' style='background:{PALETTE['panel2']};color:{PALETTE['muted']};margin-left:4px;'>
                      {"📊 Hisse" if r.asset_type == "stock" else "🪙 Emtia"}
                    </span>
                  </div>
                  <ul style='margin:12px 0 0 0; padding-left:18px; font-size:12.5px; color:{PALETTE['muted']};'>
                    {"".join(f"<li>{rt}</li>" for rt in r.rationale[:3])}
                  </ul>
                </div>
                """, unsafe_allow_html=True)

        warn = diversification_warning(top3)
        if warn:
            st.warning(warn)

    # ------------------------------------------------------------ #
    # Tüm watchlist — tablo
    # ------------------------------------------------------------ #
    st.markdown("### 📋 Tüm Watchlist")
    rows = []
    for sym in symbols:
        snap = snapshots.get(sym)
        if not snap:
            rows.append({
                "Sembol": sym, "İsim": display_name(sym),
                "Tip": "📊" if asset_type(sym) == "stock" else "🪙",
                "Fiyat": None, "Değişim": None, "Skor": None, "Karar": "Veri yok",
            })
            continue
        rows.append({
            "Sembol":  sym,
            "İsim":    display_name(sym),
            "Tip":     "📊" if snap["asset_type"] == "stock" else "🪙",
            "Fiyat":   snap.get("price"),
            "Değişim": snap.get("change_pct"),
            "Skor":    snap.get("overall_score"),
            "Karar":   snap.get("verdict") or "—",
        })
    df = pd.DataFrame(rows)
    df = df.sort_values(by="Skor", ascending=False, na_position="last")
    st.dataframe(
        df,
        column_config={
            "Fiyat":   st.column_config.NumberColumn("Fiyat (USD)", format="$%.2f"),
            "Değişim": st.column_config.NumberColumn("Günlük %", format="%.2f%%"),
            "Skor":    st.column_config.ProgressColumn(
                "Genel Skor", min_value=0, max_value=100, format="%d"),
        },
        use_container_width=True, hide_index=True,
    )

    # ------------------------------------------------------------ #
    # Son uyarılar
    # ------------------------------------------------------------ #
    alerts = db.recent_alerts(limit=10)
    if alerts:
        st.markdown("### 🚨 Son Uyarılar")
        for a in alerts:
            sev_color = {"critical": PALETTE["red"],
                         "warning":  PALETTE["orange"],
                         "info":     PALETTE["accent"]}.get(a["severity"], PALETTE["muted"])
            st.markdown(
                f"<div class='fcard' style='padding:10px 14px; border-left:3px solid {sev_color};'>"
                f"<b>{a['symbol']}</b> · {a['message']}"
                f"<div style='color:{PALETTE['muted']}; font-size:12px;'>"
                f"{a['created_at'][:16]} · {a['kind']}</div></div>",
                unsafe_allow_html=True,
            )
