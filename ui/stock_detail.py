"""
Tek sembol detay sayfası — skor halkası, boyut barları, geçmiş, temel veriler.
"""
from __future__ import annotations

import json

import streamlit as st

from config.settings import asset_type, display_name
from core import database as db
from core.news_analyzer import sentiment_label, CATEGORY_LABELS
from ui.components import (
    PALETTE, chg_badge, dim_bar_chart, fmt_cap, fmt_num, fmt_pct, fmt_x,
    score_history_chart, price_chart, score_ring, verdict_badge,
)


def render(symbol: str) -> None:
    snap = db.latest_snapshot(symbol)
    name = display_name(symbol)
    atype = asset_type(symbol)

    if not snap:
        st.warning(f"**{symbol}** için henüz snapshot yok. Sol menüden veri topla.")
        return

    payload = json.loads(snap.get("raw_payload") or "{}")
    score   = snap.get("overall_score")
    verdict = snap.get("verdict") or "—"
    color   = payload.get("verdict_color", PALETTE["muted"])
    price   = snap.get("price")
    chg     = snap.get("change_pct")

    # ---- Üst bar: isim + fiyat + halka ----
    col_left, col_right = st.columns([1, 2])
    with col_left:
        st.plotly_chart(score_ring(score, color, verdict),
                        use_container_width=True,
                        config={"displayModeBar": False})
    with col_right:
        st.markdown(f"### {name}")
        st.markdown(
            f"`{symbol}` · {'📊 Hisse' if atype == 'stock' else '🪙 Emtia ETF'}"
            f" · Son güncelleme: {snap['captured_at'][:16]}"
        )
        st.markdown(
            f"<div style='font-size:32px; font-weight:800; margin-top:8px;'>"
            f"${fmt_num(price)} "
            f"<span style='font-size:18px;'>{chg_badge(chg)}</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown(verdict_badge(verdict, color), unsafe_allow_html=True)
        st.markdown(
            f"<div style='color:{PALETTE['muted']}; margin-top:14px; line-height:1.55;'>"
            f"{payload.get('summary', '')}</div>",
            unsafe_allow_html=True,
        )

    # ---- Boyut skorları ----
    st.markdown("### Boyut Bazlı Skorlama")
    dims = payload.get("dimensions", [])
    if dims:
        # payload string olarak gelmiş olabilir; analyzer.AnalysisResult'ı
        # dataclass olarak yazdığımız için snapshot anında dict listesi olarak
        # serialize ettik. Burada lightweight bir namespace yapısı oluşturalım:
        class _D:  # pragma: no cover
            def __init__(self, d: dict) -> None:
                self.name   = d.get("name")
                self.score  = d.get("score")
                self.weight = d.get("weight")
        dim_objs = [_D(d) for d in dims]
        st.plotly_chart(dim_bar_chart(dim_objs), use_container_width=True,
                        config={"displayModeBar": False})

    # ---- Güçlü / Zayıf ----
    col_p, col_c = st.columns(2)
    with col_p:
        st.markdown("#### ✅ Güçlü Yönler")
        pros = payload.get("pros", []) or []
        if pros:
            for p in pros[:6]:
                st.markdown(f"- {p}")
        else:
            st.caption("Öne çıkan güçlü yön tespit edilmedi.")
    with col_c:
        st.markdown("#### ⚠️ Zayıf Yönler / Riskler")
        cons = payload.get("cons", []) or []
        if cons:
            for c in cons[:6]:
                st.markdown(f"- {c}")
        else:
            st.caption("Belirgin bir risk öne çıkmıyor.")

    # ---- Geçmiş grafikleri ----
    st.markdown("### 📈 Geçmiş")
    history = db.snapshot_history(symbol, days=90)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Fiyat (90 gün)**")
        st.plotly_chart(price_chart(history), use_container_width=True,
                        config={"displayModeBar": False})
    with col2:
        st.markdown("**Analiz Skoru (90 gün)**")
        st.plotly_chart(score_history_chart(history), use_container_width=True,
                        config={"displayModeBar": False})

    # ---- Temel veriler (yalnız hisse) ----
    if atype == "stock":
        st.markdown("### 📊 Temel Veriler")
        m = payload.get("raw_metrics", {}) or {}
        rows = [
            ("F/K (TTM)",      fmt_x(m.get("peTTM") or m.get("peBasicExclExtraTTM"))),
            ("PD/DD",          fmt_x(m.get("pbQuarterly") or m.get("pbAnnual"))),
            ("P/S",            fmt_x(m.get("psTTM"))),
            ("ROE",            fmt_pct(m.get("roeTTM") or m.get("roeRfy"))),
            ("Net Marj",       fmt_pct(m.get("netProfitMarginTTM"))),
            ("Brüt Marj",      fmt_pct(m.get("grossMarginTTM"))),
            ("Gelir Büyümesi", fmt_pct(m.get("revenueGrowthTTMYoy"))),
            ("EPS Büyüme",     fmt_pct(m.get("epsGrowthTTMYoy"))),
            ("Cari Oran",      fmt_x(m.get("currentRatioQuarterly"))),
            ("Borç/Özkaynak",  fmt_x(m.get("totalDebt/totalEquityQuarterly"))),
            ("Beta",           fmt_num(m.get("beta"))),
            ("Piyasa Değeri",  fmt_cap(payload.get("market_cap"))),
        ]
        cols = st.columns(4)
        for i, (label, val) in enumerate(rows):
            with cols[i % 4]:
                st.markdown(
                    f"<div class='fcard' style='padding:12px; margin-bottom:8px;'>"
                    f"<div style='color:{PALETTE['muted']}; font-size:11px;'>{label}</div>"
                    f"<div style='font-size:17px; font-weight:700;'>{val}</div></div>",
                    unsafe_allow_html=True,
                )

    # ---- Son haberler (kısa) ----
    st.markdown("### 📰 Son Haberler (özet)")
    news = db.recent_news(symbol, limit=6)
    if not news:
        st.caption("Bu sembol için kayıtlı haber yok.")
        return
    for n in news:
        slab, scol = sentiment_label(n.get("sentiment"))
        cat_label = CATEGORY_LABELS.get(n.get("category", "other"), "📰")
        st.markdown(
            f"<div class='news-item'>"
            f"<div style='flex:1;'>"
            f"<div class='news-title'>"
            f"<a href='{n.get('url', '#')}' target='_blank'>{n.get('headline', '')}</a></div>"
            f"<div class='news-meta'>{n.get('source', '')} · "
            f"{(n.get('published_at') or '')[:10]} · "
            f"<span class='pill' style='background:{scol}22;color:{scol};'>"
            f"{slab} ({(n.get('sentiment') or 0):+.2f})</span> "
            f"<span class='pill' style='background:{PALETTE['panel2']};color:{PALETTE['muted']};'>{cat_label}</span>"
            f"</div></div></div>",
            unsafe_allow_html=True,
        )
