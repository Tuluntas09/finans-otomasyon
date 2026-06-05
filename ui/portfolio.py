"""
Yatırım Önerisi — design pages-extra.jsx RecPage birebir port.
"""
from __future__ import annotations

import streamlit as st

from config.settings import load_watchlist
from core.recommender import recommend_all
from ui.components import (
    PALETTE, decision_badge, icon, kind_badge, kpi, page_head, panel,
    score_color,
)


def render(symbols: list[str]) -> None:
    wl = load_watchlist()
    meta = {s["symbol"]: (s.get("name", s["symbol"]), "stock")
            for s in wl["stocks"]}
    meta.update({s["symbol"]: (s.get("name", s["symbol"]), "commodity")
                 for s in wl["commodities"]})
    triples = [(sym, *meta[sym]) for sym in symbols if sym in meta]
    recs = recommend_all(triples)

    st.markdown(
        "<div class='page'>" + page_head(
            "Yatırım Önerisi",
            sub="Final skor = Analiz %50 + Trend %20 + Sentiment %15 + Momentum %15",
            meta=f"{len(recs)} sembol değerlendirildi",
            meta_status="ok" if recs else "warn",
        ),
        unsafe_allow_html=True,
    )

    if not recs:
        st.markdown(
            panel("Veri Yok",
                  "<div class='muted'>En az 1 snapshot çek ki öneri çıksın.</div>",
                  ico="rec") + "</div>",
            unsafe_allow_html=True,
        )
        return

    # ────────────────────── KPI strip — 5 aksiyon sayımı ──────────────────────
    cnt = {}
    for r in recs:
        cnt[r.action] = cnt.get(r.action, 0) + 1
    actions = [
        ("AL",       PALETTE["d_al"]),
        ("BİRİKTİR", PALETTE["d_biriktir"]),
        ("TUT",      PALETTE["d_tut"]),
        ("AZALT",    PALETTE["d_azalt"]),
        ("SAT",      PALETTE["d_sat"]),
    ]
    kpi_strip = "<div class='grid' style='grid-template-columns:repeat(5,1fr); margin-bottom:16px;'>"
    for label, col in actions:
        kpi_strip += kpi(label, str(cnt.get(label, 0)),
                         color=col,
                         foot="<span class='muted'>sembol</span>")
    kpi_strip += "</div>"
    st.markdown(kpi_strip, unsafe_allow_html=True)

    # ────────────────────── İlk 5 öneri kartları (5 sütun grid) ──────────────────────
    st.markdown(
        "<div class='sectionlabel' style='margin-bottom:10px;'>İlk 5 Öneri</div>",
        unsafe_allow_html=True,
    )

    top5 = recs[:5]
    comps_meta = [
        ("Analiz",       "%50", "analysis"),
        ("Skor Trendi",  "%20", "trend"),
        ("Sentiment",    "%15", "sentiment"),
        ("3A Momentum",  "%15", "momentum"),
    ]

    cards_html = "<div class='grid' style='grid-template-columns:repeat(5,1fr); margin-bottom:18px; gap:14px;'>"
    for i, r in enumerate(top5):
        score_col = score_color(r.final_score)
        kind = "stock" if r.asset_type == "stock" else "etf"

        # Bileşen barları
        comps_rows = ""
        for label, weight, key in comps_meta:
            v = r.components.get(key)
            if v is None:
                bar = "<div class='dim-track' style='flex:1;'></div>"
                v_str = "—"
            else:
                col = score_color(v)
                bar = (f"<div class='dim-track' style='flex:1;'>"
                       f"<div class='dim-fill' style='width:{v}%; background:{col};'></div></div>")
                v_str = str(v)
            comps_rows += (
                f"<div class='row between' style='font-size:11px;'>"
                f"<span class='muted'>{label} <span class='faint'>{weight}</span></span>"
                f"<div class='row' style='gap:7px; width:92px;'>{bar}"
                f"<span class='mono' style='width:18px; text-align:right; color:var(--tx);'>{v_str}</span>"
                f"</div></div>"
            )

        reasons_html = "".join(
            f"<li class='tiny' style='color:var(--tx); display:flex; gap:6px; "
            f"line-height:1.35;'>"
            f"<span style='color:var(--accent);'>›</span>{rt}</li>"
            for rt in r.rationale
        )

        cards_html += (
            f"<div class='hl-card' style='gap:14px;'>"
            f"<div class='hl-rank'>#{i + 1}</div>"
            f"<div class='hl-top'>"
            f"<span class='hl-tk'>{r.symbol}</span>{kind_badge(kind)}"
            f"</div>"
            f"<div class='muted tiny' style='margin-top:-6px;'>{r.name[:24]}</div>"
            f"<div class='row between' style='align-items:flex-end;'>"
            f"<div>"
            f"<div class='faint tiny' style='text-transform:uppercase; "
            f"letter-spacing:0.05em;'>Final Skor</div>"
            f"<div class='hl-score-big' style='color:{score_col};'>{r.final_score}</div>"
            f"</div>"
            f"{decision_badge(r.action)}"
            f"</div>"
            f"<div style='display:flex; flex-direction:column; gap:6px; "
            f"padding-top:10px; border-top:1px solid var(--line-faint);'>{comps_rows}</div>"
            f"<div style='padding-top:10px; border-top:1px solid var(--line-faint);'>"
            f"<div class='faint tiny' style='text-transform:uppercase; "
            f"letter-spacing:0.05em; margin-bottom:6px;'>Neden</div>"
            f"<ul style='margin:0; padding:0; list-style:none; display:flex; "
            f"flex-direction:column; gap:5px;'>{reasons_html}</ul>"
            f"</div></div>"
        )
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)

    # ────────────────────── Tüm öneriler tablosu ──────────────────────
    rows_html = ""
    for i, r in enumerate(recs):
        kind = "stock" if r.asset_type == "stock" else "etf"
        col = score_color(r.final_score)
        rows_html += (
            f"<tr>"
            f"<td class='mono faint'>{i + 1}</td>"
            f"<td><span class='tk'>{r.symbol}</span> {kind_badge(kind)} "
            f"<span class='nm'>{r.name[:24]}</span></td>"
            f"<td>{decision_badge(r.action)}</td>"
            f"<td class='r mono'>{r.components.get('analysis') or '—'}</td>"
            f"<td class='r mono'>{r.components.get('trend') or '—'}</td>"
            f"<td class='r mono'>{r.components.get('sentiment') or '—'}</td>"
            f"<td class='r mono'>{r.components.get('momentum') or '—'}</td>"
            f"<td class='r'><span class='mono' style='font-size:14px; "
            f"font-weight:600; color:{col};'>{r.final_score}</span></td>"
            f"</tr>"
        )
    tbl = (
        f"<div class='tbl-wrap'><table class='tbl'>"
        f"<thead><tr>"
        f"<th>#</th><th>Sembol</th><th>Aksiyon</th>"
        f"<th class='r'>Analiz</th><th class='r'>Trend</th>"
        f"<th class='r'>Sentiment</th><th class='r'>Momentum</th>"
        f"<th class='r'>Final</th>"
        f"</tr></thead>"
        f"<tbody>{rows_html}</tbody></table></div>"
    )
    st.markdown(
        panel("Tüm Öneriler", tbl, ico="rec",
              right="<span class='panel-note'>final skora göre sıralı</span>",
              pad=False),
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='disclaimer'>⚠ DISCLAIMER · Bu skorlar otomatik, kural "
        "tabanlı hesaplamalardır. Geçmiş performans gelecek getirisini garanti "
        "etmez. Yatırım tavsiyesi DEĞİLDİR.</div>",
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)  # .page
