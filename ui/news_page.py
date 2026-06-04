"""
Haber sayfası — tüm watchlist için son haberler, sentiment dağılımı, filtreler.
"""
from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from config.settings import display_name
from core import database as db
from core.news_analyzer import (
    CATEGORY_LABELS, aggregate, sentiment_label,
)
from ui.components import PALETTE, sentiment_donut


def render(symbols: list[str]) -> None:
    st.markdown("## 📰 Haber Akışı & Sentiment")
    st.caption("Tüm watchlist'in son 14 günlük haberleri, sentiment skoruyla.")

    # Filtreler
    col_a, col_b, col_c = st.columns([2, 2, 1])
    with col_a:
        selected = st.multiselect(
            "Sembol",
            options=symbols,
            default=symbols,
            format_func=lambda s: f"{s} — {display_name(s)}",
        )
    with col_b:
        cats = list(CATEGORY_LABELS.keys())
        cat_filter = st.multiselect(
            "Kategori", options=cats, default=cats,
            format_func=lambda c: CATEGORY_LABELS.get(c, c),
        )
    with col_c:
        only_significant = st.checkbox("Yalnız önemli haberler (|sentiment|≥0.3)")

    # Tüm haberleri topla
    all_news: list[dict[str, Any]] = []
    for sym in selected:
        for n in db.recent_news(sym, limit=30):
            n["symbol"] = sym
            all_news.append(n)

    if not all_news:
        st.info("Seçilen sembollerde kayıtlı haber yok. Veri toplama job'unu çalıştır.")
        return

    if cat_filter:
        all_news = [n for n in all_news if n.get("category") in cat_filter]
    if only_significant:
        all_news = [n for n in all_news if (n.get("sentiment") or 0) and
                    abs(n["sentiment"]) >= 0.3]

    all_news.sort(key=lambda n: n.get("published_at") or "", reverse=True)

    # ---- Toplam dağılım ----
    agg = aggregate(all_news)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Haber sayısı", agg["count"])
    c2.metric("Ortalama sentiment",
              f"{agg['avg_sentiment']:+.2f}" if agg["avg_sentiment"] is not None else "—")
    c3.metric("Pozitif", agg["positive_count"])
    c4.metric("Negatif", agg["negative_count"])

    col_donut, col_bar = st.columns([1, 2])
    with col_donut:
        st.plotly_chart(sentiment_donut(agg), use_container_width=True,
                        config={"displayModeBar": False})
    with col_bar:
        # Kategori dağılımı
        cat_df = pd.DataFrame([
            {"Kategori": CATEGORY_LABELS.get(c, c), "Adet": n}
            for c, n in agg["category_breakdown"].items()
        ]).sort_values("Adet", ascending=False)
        if not cat_df.empty:
            st.markdown("**Kategori dağılımı**")
            st.bar_chart(cat_df.set_index("Kategori"))

    # ---- Sembol bazlı sentiment tablosu ----
    st.markdown("### Sembol Bazlı Sentiment (son 14 gün)")
    per_symbol = []
    for sym in selected:
        avg = db.avg_sentiment(sym, days=14)
        recent_n = db.recent_news(sym, limit=30)
        per_symbol.append({
            "Sembol":    sym,
            "İsim":      display_name(sym),
            "Haber #":   len(recent_n),
            "Sentiment": avg,
            "Etiket":    sentiment_label(avg)[0],
        })
    sdf = pd.DataFrame(per_symbol).sort_values("Sentiment", ascending=False,
                                                na_position="last")
    st.dataframe(
        sdf,
        column_config={
            "Sentiment": st.column_config.ProgressColumn(
                "Sentiment", min_value=-1, max_value=1, format="%.2f"),
        },
        hide_index=True, use_container_width=True,
    )

    # ---- Haber akışı ----
    st.markdown("### Haber Akışı")
    for n in all_news[:80]:
        slab, scol = sentiment_label(n.get("sentiment"))
        cat = CATEGORY_LABELS.get(n.get("category", "other"), "📰")
        st.markdown(
            f"<div class='news-item'>"
            f"<div style='flex:1;'>"
            f"<div class='news-title'>"
            f"<span class='pill' style='background:{PALETTE['accent']}22;color:{PALETTE['accent']};margin-right:6px;'>{n['symbol']}</span>"
            f"<a href='{n.get('url', '#')}' target='_blank'>{n.get('headline', '')}</a></div>"
            f"<div class='news-meta'>{n.get('source', '')} · "
            f"{(n.get('published_at') or '')[:10]} · "
            f"<span class='pill' style='background:{scol}22;color:{scol};'>{slab} ({(n.get('sentiment') or 0):+.2f})</span> "
            f"<span class='pill' style='background:{PALETTE['panel2']};color:{PALETTE['muted']};'>{cat}</span>"
            f"</div></div></div>",
            unsafe_allow_html=True,
        )
