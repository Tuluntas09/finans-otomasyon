"""
Haberler — design pages-extra.jsx NewsPage birebir port.
"""
from __future__ import annotations

import streamlit as st

from config.settings import display_name
from core import database as db
from ui.components import (
    PALETTE, h, icon, kpi, page_head, panel, sentiment_donut,
)


def render(symbols: list[str]) -> None:
    # Tüm haberleri topla
    all_news = []
    for sym in symbols:
        for n in db.recent_news(sym, limit=30):
            n["symbol"] = sym
            all_news.append(n)
    all_news.sort(key=lambda n: n.get("published_at") or "", reverse=True)

    # ────────────────────── page-head ──────────────────────
    st.markdown(
        "<div class='page'>" + page_head(
            "Haberler",
            sub="14 günlük haber akışı ve VADER sentiment analizi",
            meta=f"{len(all_news)} haber indeksli",
            meta_status="ok",
        ),
        unsafe_allow_html=True,
    )

    if not all_news:
        st.markdown(
            panel("Veri Yok",
                  "<div class='muted'>Henüz haber yok. Sol menüden "
                  "<b>Şimdi Çalıştır</b>'a basarak veri çek.</div>",
                  ico="news") + "</div>",
            unsafe_allow_html=True,
        )
        return

    # ────────────────────── Filtreler ──────────────────────
    cats_seen = sorted({(n.get("category") or "other") for n in all_news})

    st.markdown(
        f"<div class='panel' style='margin-bottom:16px;'>"
        f"<div class='panel-head'>"
        f"<div class='panel-title'><span class='ico'>{icon('filter')}</span>Filtreler</div>"
        f"</div>"
        f"<div class='panel-body'>",
        unsafe_allow_html=True,
    )

    col_sym, col_cat, col_imp = st.columns([2, 2, 1])
    with col_sym:
        sel_syms = st.multiselect(
            "Sembol", options=symbols, default=[],
            format_func=lambda s: s,
            placeholder="Tüm semboller",
        )
    with col_cat:
        sel_cats = st.multiselect(
            "Kategori", options=cats_seen, default=[],
            placeholder="Tüm kategoriler",
        )
    with col_imp:
        only_imp = st.checkbox("Sadece önemli (|sent| ≥ 0.30)")

    st.markdown("</div></div>", unsafe_allow_html=True)

    # Filtre uygula
    filtered = all_news
    if sel_syms:
        filtered = [n for n in filtered if n["symbol"] in sel_syms]
    if sel_cats:
        filtered = [n for n in filtered if (n.get("category") or "other") in sel_cats]
    if only_imp:
        filtered = [n for n in filtered if abs(n.get("sentiment") or 0) >= 0.30]

    # ────────────────────── KPI ──────────────────────
    avg_sent = (sum(n.get("sentiment", 0) for n in filtered) / len(filtered)
                if filtered else 0)
    pos_cnt = sum(1 for n in filtered if (n.get("sentiment") or 0) > 0.08)
    neg_cnt = sum(1 for n in filtered if (n.get("sentiment") or 0) < -0.08)
    neu_cnt = len(filtered) - pos_cnt - neg_cnt

    avg_color = (PALETTE["pos"] if avg_sent > 0.08
                 else PALETTE["neg"] if avg_sent < -0.08
                 else PALETTE["tx_hi"])

    kpi_strip = (
        "<div class='grid' style='grid-template-columns:repeat(4,1fr); margin-bottom:16px;'>"
        + kpi("Toplam Haber", str(len(filtered)),
              foot="<span class='muted'>filtreli</span>")
        + kpi("Ortalama Sentiment",
              ("+" if avg_sent > 0 else "") + f"{avg_sent:.2f}",
              color=avg_color, accent=True,
              foot="<span class='muted'>−1 .. +1 ölçeği</span>")
        + kpi("Pozitif", str(pos_cnt), color=PALETTE["pos"],
              foot=f"<span class='muted'>%{round(pos_cnt/max(1,len(filtered))*100)}</span>")
        + kpi("Negatif", str(neg_cnt), color=PALETTE["neg"],
              foot=f"<span class='muted'>%{round(neg_cnt/max(1,len(filtered))*100)}</span>")
        + "</div>"
    )
    st.markdown(kpi_strip, unsafe_allow_html=True)

    # ────────────────────── Donut + Kategori + Sembol tablo (3 sütun) ──────────────────────
    col1, col2, col3 = st.columns([0.9, 1, 1.2])

    with col1:
        st.markdown(
            f"<div class='panel'>"
            f"<div class='panel-head'>"
            f"<div class='panel-title'><span class='ico'>{icon('gauge')}</span>Sentiment Dağılımı</div>"
            f"</div>"
            f"<div class='panel-body'>",
            unsafe_allow_html=True,
        )
        fig = sentiment_donut(pos_cnt, neu_cnt, neg_cnt)
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown("</div></div>", unsafe_allow_html=True)

    with col2:
        # Kategori dağılımı — dim-row tarzı
        cat_count = {}
        for n in filtered:
            c = n.get("category") or "other"
            cat_count[c] = cat_count.get(c, 0) + 1
        max_cat = max(cat_count.values()) if cat_count else 1
        rows = ""
        for c, n in sorted(cat_count.items(), key=lambda x: -x[1]):
            pct = n / max_cat * 100
            rows += (
                f"<div class='dim-row' style='grid-template-columns:130px 1fr 26px;'>"
                f"<div class='dim-name'>{c}</div>"
                f"<div class='dim-track'><div class='dim-fill' "
                f"style='width:{pct}%; background:var(--accent);'></div></div>"
                f"<div class='dim-val'>{n}</div></div>"
            )
        st.markdown(
            panel("Kategori Dağılımı",
                  f"<div style='display:flex; flex-direction:column; gap:6px;'>"
                  f"{rows or '<div class=\"muted tiny\">Yok</div>'}</div>",
                  ico="list"),
            unsafe_allow_html=True,
        )

    with col3:
        # Sembol bazlı sentiment tablo
        sym_agg = []
        for sym in symbols:
            ns = [n for n in filtered if n["symbol"] == sym]
            if not ns:
                continue
            avg = sum((n.get("sentiment") or 0) for n in ns) / len(ns)
            sym_agg.append((sym, display_name(sym), len(ns), avg))
        sym_agg.sort(key=lambda x: x[3], reverse=True)

        rows_html = ""
        for sym, name, count, avg in sym_agg:
            sc = "pos" if avg > 0.08 else ("neg" if avg < -0.08 else "neu")
            avg_text = ("+" if avg > 0 else "") + f"{avg:.2f}"
            rows_html += (
                f"<tr>"
                f"<td><span class='tk'>{sym}</span> "
                f"<span class='nm'>{name[:18]}</span></td>"
                f"<td class='r mono'>{count}</td>"
                f"<td class='r'><span class='sent-chip {sc}'>{avg_text}</span></td>"
                f"</tr>"
            )
        tbl = (
            f"<div class='tbl-wrap'><table class='tbl'>"
            f"<thead><tr><th>Sembol</th><th class='r'>Haber</th>"
            f"<th class='r'>Ort. Sentiment</th></tr></thead>"
            f"<tbody>{rows_html}</tbody></table></div>"
        )
        st.markdown(
            panel("Sembol Bazlı Sentiment", tbl, ico="detail", pad=False),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ────────────────────── Haber akışı (2 sütun grid) ──────────────────────
    items_html = ""
    for n in filtered[:80]:
        sent_v = n.get("sentiment") or 0
        sc = "pos" if sent_v > 0.08 else ("neg" if sent_v < -0.08 else "neu")
        sent_text = ("+" if sent_v > 0 else "") + f"{sent_v:.2f}"
        published = (n.get("published_at") or "")[:10]
        time_part = (n.get("published_at") or "")[11:16]
        cat = n.get("category") or "other"
        items_html += (
            f"<div class='news-item'>"
            f"<div class='news-thumb'>"
            f"<span class='nt'>{n['symbol'][:3]}</span></div>"
            f"<div class='news-body'>"
            f"<div class='news-title'>"
            f"<a href='{h(n.get('url', '#'))}' target='_blank'>{h(n.get('headline', ''))}</a>"
            f"</div>"
            f"<div class='news-meta'>"
            f"<span>{n.get('source', '')}</span>"
            f"<span class='sep'>·</span>"
            f"<span>{published} {time_part}</span>"
            f"</div>"
            f"<div class='news-chips'>"
            f"<span class='sent-chip {sc}'>{sent_text}</span>"
            f"<span class='cat-chip'>{cat}</span>"
            f"</div></div></div>"
        )
    feed_body = (
        f"<div class='grid' style='grid-template-columns:1fr 1fr; "
        f"gap:0 28px; padding:4px 16px 8px;'>{items_html}</div>"
        if items_html else
        "<div class='muted' style='padding:20px;'>Filtrelere uyan haber yok</div>"
    )
    st.markdown(
        panel("Haber Akışı", feed_body, ico="news",
              right=f"<span class='panel-note'>{len(filtered)} haber</span>",
              pad=False),
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)  # .page
