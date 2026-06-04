"""
Portföy önerisi sayfası — recommend_all sonucunu zenginleştirilmiş listede gösterir.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config.settings import asset_type, display_name, load_watchlist
from core.recommender import diversification_warning, recommend_all
from ui.components import PALETTE


def render(symbols: list[str]) -> None:
    st.markdown("## 💼 Yatırım Önerisi")
    st.caption(
        "Her sembol için: 6 boyutlu analiz skoru (%50) + skor trendi (%20) "
        "+ haber sentiment'i (%15) + 3 ay momentum (%15)."
    )

    wl = load_watchlist()
    meta = {s["symbol"]: (s.get("name", s["symbol"]), "stock") for s in wl["stocks"]}
    meta.update({s["symbol"]: (s.get("name", s["symbol"]), "commodity")
                 for s in wl["commodities"]})

    triples = [(sym, *meta[sym]) for sym in symbols if sym in meta]
    recs = recommend_all(triples)
    if not recs:
        st.info("Henüz yeterli veri yok. En az 1 snapshot çek ki bir öneri çıksın.")
        return

    # ---- Aksiyon dağılımı ----
    counts = {}
    for r in recs:
        counts[r.action] = counts.get(r.action, 0) + 1
    cols = st.columns(5)
    for i, action in enumerate(["AL", "BİRİKTİR", "TUT", "AZALT", "SAT"]):
        cols[i].metric(action, counts.get(action, 0))

    warn = diversification_warning(recs)
    if warn:
        st.warning(warn)

    # ---- Detaylı liste ----
    for r in recs:
        st.markdown(
            f"""
            <div class='fcard' style='border-left:4px solid {r.action_color};'>
              <div style='display:flex; justify-content:space-between; align-items:flex-start;'>
                <div style='flex:1;'>
                  <div style='font-size:20px; font-weight:800;'>
                    {r.symbol}
                    <span style='font-size:14px; color:{PALETTE['muted']}; font-weight:500;'>· {r.name}</span>
                  </div>
                  <div style='margin-top:6px;'>
                    <span class='badge' style='background:{r.action_color}22;color:{r.action_color};'>{r.action}</span>
                    <span class='pill' style='background:{PALETTE['panel2']};color:{PALETTE['muted']};margin-left:4px;'>
                      {"📊 Hisse" if r.asset_type == "stock" else "🪙 Emtia ETF"}
                    </span>
                  </div>
                  <ul style='margin:10px 0 0 0; padding-left:18px; color:{PALETTE['muted']}; font-size:13px;'>
                    {"".join(f"<li>{rt}</li>" for rt in r.rationale)}
                  </ul>
                </div>
                <div style='text-align:right; min-width:120px;'>
                  <div style='font-size:32px; font-weight:800; color:{r.action_color};'>{r.final_score}</div>
                  <div style='font-size:11px; color:{PALETTE['muted']};'>FİNAL SKOR / 100</div>
                </div>
              </div>
              <div style='margin-top:12px; display:flex; gap:18px; font-size:12px; color:{PALETTE['muted']};'>
                <span>Analiz: <b style='color:{PALETTE['text']}'>{r.components['analysis'] or '—'}</b></span>
                <span>Trend: <b style='color:{PALETTE['text']}'>{r.components['trend'] or '—'}</b></span>
                <span>Sentiment: <b style='color:{PALETTE['text']}'>{r.components['sentiment'] or '—'}</b></span>
                <span>Momentum: <b style='color:{PALETTE['text']}'>{r.components['momentum'] or '—'}</b></span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div style='font-size:12px; color:{PALETTE['muted']}; margin-top:16px;'>"
        "⚠️ Bu skorlar kural tabanlı bir hesaplamadır, yatırım tavsiyesi değildir. "
        "Geçmiş performans gelecek getirisini garanti etmez. Kendi araştırmanı yap.</div>",
        unsafe_allow_html=True,
    )
