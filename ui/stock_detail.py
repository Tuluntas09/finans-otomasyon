"""
Sembol Detayı — design pages-main.jsx DetailPage birebir port.

Düzen:
  page-head (geri butonu + başlık + select)
  Hero band (sembol kutusu + statline: Fiyat/Gün/Skor/Karar) + özet metin
  2 sütun: Performans (toggle Fiyat/Skor + AreaChart + getiriler) | Skor Kırılımı (DimBar'lar)
  2 sütun: Bull/Bear Case | (52H + Analist) dikey
  Temel Veriler grid 4 sütun
  Son Haberler 2 sütun
"""
from __future__ import annotations

import json

import streamlit as st

from config.settings import asset_type, display_name
from core import database as db
from core.price_history import get_ohlcv
from ui.components import (
    PALETTE, area_chart, decision_badge, dim_bar, fmt_cap, fmt_chg_class,
    fmt_chg_str, fmt_num, fmt_pct, fmt_price, fmt_x, h, icon, kind_badge,
    page_head, panel, score_color, sent_chip,
)


def render(symbol: str, all_symbols: list[str]) -> None:
    snap = db.latest_snapshot(symbol)
    name = display_name(symbol)
    atype = asset_type(symbol)
    kind = "stock" if atype == "stock" else "etf"

    if not snap:
        st.markdown(
            "<div class='page'>" + page_head(
                f"{symbol}", sub="Veri yok",
            ) +
            f"<div class='panel'><div class='panel-body muted'>"
            f"Bu sembol için henüz snapshot yok. Sol menüden "
            f"<b>Şimdi Çalıştır</b>'a bas.</div></div></div>",
            unsafe_allow_html=True,
        )
        return

    payload = json.loads(snap.get("raw_payload") or "{}")
    price = snap.get("price")
    day = snap.get("change_pct")
    score = snap.get("overall_score") or 0
    verdict = snap.get("verdict") or "—"
    summary = payload.get("summary") or ""

    # ────────────────────── page-head ──────────────────────
    st.markdown(
        "<div class='page'>" + page_head(
            "Sembol Detayı",
            sub="Derinlemesine analiz raporu",
        ),
        unsafe_allow_html=True,
    )

    # ────────────────────── Hero band ──────────────────────
    day_cls = fmt_chg_class(day)
    day_str = fmt_chg_str(day)
    day_color = PALETTE["pos"] if day_cls == "pos" else (PALETTE["neg"] if day_cls == "neg" else PALETTE["tx"])

    # Sektör/grup etiketi
    group_label = ""
    if atype == "commodity":
        from config.settings import load_watchlist
        wl = load_watchlist()
        for s in wl["commodities"]:
            if s["symbol"] == symbol:
                group_label = s.get("underlying", "Emtia ETF")
                break
    else:
        group_label = "Hisse Senedi"

    hero = (
        f"<div class='panel' style='margin-bottom:16px;'>"
        f"<div style='padding:18px 22px; display:flex; align-items:center; "
        f"justify-content:space-between; gap:24px; flex-wrap:wrap;'>"
        # Sol blok: avatar + sembol + isim
        f"<div class='row' style='gap:16px;'>"
        f"<div style='width:52px; height:52px; border-radius:12px; "
        f"background:var(--bg-elev); border:1px solid var(--line); "
        f"display:grid; place-items:center; font-family:var(--f-mono); "
        f"font-weight:600; font-size:17px; color:var(--tx-hi);'>"
        f"{symbol[:2]}</div>"
        f"<div>"
        f"<div class='row' style='gap:10px;'>"
        f"<span style='font-family:var(--f-mono); font-size:24px; "
        f"font-weight:600; color:var(--tx-hi); letter-spacing:-0.01em;'>{symbol}</span>"
        f"{kind_badge(kind)}"
        f"<span class='badge badge-soft'>{group_label}</span>"
        f"</div>"
        f"<div class='muted' style='font-size:13px; margin-top:3px;'>{name}</div>"
        f"</div></div>"
        # Sağ blok: stat satırı
        f"<div class='statline'>"
        f"<div class='stat'>"
        f"<span class='stat-k'>Fiyat</span>"
        f"<span class='stat-v'>{fmt_price(price)}</span></div>"
        f"<div class='stat'>"
        f"<span class='stat-k'>Gün</span>"
        f"<span class='stat-v' style='color:{day_color};'>{day_str}</span></div>"
        f"<div class='stat'>"
        f"<span class='stat-k'>Genel Skor</span>"
        f"<span class='stat-v' style='color:{score_color(score)};'>"
        f"{score}<span style='font-size:13px; color:var(--tx-faint);'>/100</span></span></div>"
        f"<div class='stat'>"
        f"<span class='stat-k'>Karar</span>"
        f"<div style='margin-top:2px;'>{decision_badge(verdict, big=True)}</div></div>"
        f"</div>"
        f"</div>"
        # Özet metin
        f"<div style='padding:13px 22px; border-top:1px solid var(--line); "
        f"font-size:13px; color:var(--tx); line-height:1.5; background:var(--bg-inset);'>"
        f"{summary}</div>"
        f"</div>"
    )
    st.markdown(hero, unsafe_allow_html=True)

    # ────────────────────── Performans + Skor Kırılımı (2 sütun) ──────────────────────
    col_l, col_r = st.columns([1.35, 1])

    # SOL — Performans (toggle Fiyat/Skor + grafik + getiri satırı)
    with col_l:
        # Chart mode toggle — session state
        mode_key = f"chart_mode_{symbol}"
        mode = st.session_state.get(mode_key, "price")
        # Toggle butonu Streamlit'in radio'su ile yapalım, sonra CSS ile seg gibi göstereceğiz
        # Daha kolay yol: 2 buton koyalım
        st.markdown(
            f"<div class='panel'>"
            f"<div class='panel-head'>"
            f"<div class='panel-title'><span class='ico'>{icon('detail')}</span>Performans</div>"
            f"<div class='seg' style='gap:0;'>",
            unsafe_allow_html=True,
        )
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Fiyat 90G",
                         key=f"btn_price_{symbol}",
                         use_container_width=True,
                         type=("primary" if mode == "price" else "secondary")):
                st.session_state[mode_key] = "price"
                st.rerun()
        with col_btn2:
            if st.button("Skor 90G",
                         key=f"btn_score_{symbol}",
                         use_container_width=True,
                         type=("primary" if mode == "score" else "secondary")):
                st.session_state[mode_key] = "score"
                st.rerun()
        st.markdown("</div></div>", unsafe_allow_html=True)

        # Mum/grafik verisi
        fig = None
        if mode == "price":
            # Fiyat grafiği — yfinance (gerçek 90g OHLCV) öncelikli
            df_ohlcv = get_ohlcv(symbol, days=90)
            if not df_ohlcv.empty and "Close" in df_ohlcv.columns:
                yf_times  = [str(d)[:10] for d in df_ohlcv.index]
                yf_values = df_ohlcv["Close"].dropna().tolist()
                if yf_values:
                    fig = area_chart(yf_times[:len(yf_values)], yf_values,
                                     color=PALETTE["accent"], y_prefix="$",
                                     height=230)
            # yfinance boşsa DB snapshot fallback
            if fig is None:
                history = db.snapshot_history(symbol, days=90)
                if history:
                    times  = [h["captured_at"][:10] for h in history]
                    values = [h["price"] for h in history if h["price"] is not None]
                    if values:
                        fig = area_chart(times[:len(values)], values,
                                         color=PALETTE["accent"], y_prefix="$",
                                         height=230)
        else:
            # Skor grafiği — DB snapshot'larından (tek kaynak)
            history = db.snapshot_history(symbol, days=90)
            if history:
                times  = [h["captured_at"][:10] for h in history]
                values = [h["overall_score"] for h in history
                          if h["overall_score"] is not None]
                if values:
                    fig = area_chart(times[:len(values)], values,
                                     color=score_color(score), y_prefix="",
                                     height=230)

        st.markdown(f"<div class='panel-body' style='padding-top:8px;'>",
                    unsafe_allow_html=True)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})
        else:
            st.markdown(
                f"<div class='muted' style='padding:40px 0; text-align:center;'>"
                f"Henüz yeterli geçmiş yok</div>",
                unsafe_allow_html=True,
            )

        # Getiri satırı (5 sütun)
        returns = (payload.get("returns") or {})
        labels = [("5 Gün", "d5"), ("1 Ay", "m1"), ("3 Ay", "m3"),
                  ("YBB", "ytd"), ("1 Yıl", "y1")]
        ret_html = ("<div class='row between' style='margin-top:10px; "
                    "padding-top:12px; border-top:1px solid var(--line-faint);'>")
        for lbl, key in labels:
            v = returns.get(key)
            cls = fmt_chg_class(v)
            c = (PALETTE["pos"] if cls == "pos" else
                 PALETTE["neg"] if cls == "neg" else PALETTE["tx"])
            txt = ("+" if (v or 0) > 0 else "") + f"{(v or 0):.2f}%" if v is not None else "—"
            ret_html += (
                f"<div style='text-align:center;'>"
                f"<div class='faint tiny' style='text-transform:uppercase; "
                f"letter-spacing:0.05em; margin-bottom:4px;'>{lbl}</div>"
                f"<div class='mono' style='font-size:13.5px; font-weight:600; "
                f"color:{c};'>{txt}</div></div>"
            )
        ret_html += "</div></div></div>"  # close panel-body & panel
        st.markdown(ret_html, unsafe_allow_html=True)

    # SAĞ — Skor Kırılımı
    with col_r:
        dims = payload.get("dimensions", []) or []
        if dims:
            rows_html = ""
            for d in dims:
                rows_html += dim_bar(d.get("name", d.get("key", "—")),
                                     d.get("score"))
            st.markdown(
                panel("Skor Kırılımı", rows_html, ico="gauge",
                      right=f"<span class='panel-note'>{len(dims)} boyut</span>"),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                panel("Skor Kırılımı",
                      "<div class='muted'>Boyut verisi yok</div>",
                      ico="gauge"),
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ────────────────────── Bull/Bear + (52H/Analist) ──────────────────────
    col_l2, col_r2 = st.columns([1.35, 1])

    # SOL — Bull Case / Bear Case (yan yana iki sütun)
    with col_l2:
        bull = payload.get("pros", []) or []
        bear = payload.get("cons", []) or []
        bull_li = "".join(f"<li>{x}</li>" for x in bull[:6]) or "<li class='muted'>Yok</li>"
        bear_li = "".join(f"<li>{x}</li>" for x in bear[:6]) or "<li class='muted'>Yok</li>"
        body_html = (
            f"<div class='grid' style='grid-template-columns:1fr 1fr; gap:0;'>"
            f"<div class='case-col' style='border-right:1px solid var(--line);'>"
            f"<div class='case-head bull'>{icon('arrowUp', w=14)} Güçlü Yönler</div>"
            f"<ul class='case-list bull'>{bull_li}</ul>"
            f"</div>"
            f"<div class='case-col'>"
            f"<div class='case-head bear'>{icon('arrowDown', w=14)} Zayıf Yönler</div>"
            f"<ul class='case-list bear'>{bear_li}</ul>"
            f"</div></div>"
        )
        st.markdown(
            panel("Bull Case / Bear Case", body_html, ico="layers", pad=False),
            unsafe_allow_html=True,
        )

    # SAĞ — 52 Hafta Bandı + Analist (dikey)
    with col_r2:
        # 52H bandı
        tech = payload.get("technical", {}) or {}
        lo, hi = tech.get("lo"), tech.get("hi")
        if lo is not None and hi is not None and hi > lo and price is not None:
            pct = (price - lo) / (hi - lo) * 100
            pct = max(2, min(98, pct))
            band_html = (
                f"<div class='band'>"
                f"<div class='band-track'>"
                f"<div class='band-fill' style='width:{pct}%;'></div>"
                f"<div class='band-marker' data-v='{fmt_price(price)}' "
                f"style='left:{pct}%;'></div>"
                f"</div>"
                f"<div class='band-ends'>"
                f"<span>dip <b>{fmt_price(lo)}</b></span>"
                f"<span>zirve <b>{fmt_price(hi)}</b></span>"
                f"</div></div>"
            )
        else:
            band_html = "<div class='muted'>52H verisi yok</div>"
        st.markdown(panel("52 Hafta Bandı", band_html, ico="detail"),
                    unsafe_allow_html=True)
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

        # Analist konsensüsü
        analyst_dim = next((d for d in (payload.get("dimensions") or [])
                            if d.get("key") == "analyst"), None)
        details = (analyst_dim or {}).get("details") or {}
        has_analyst = any(details.get(k, 0) for k in
                          ("strongBuy", "buy", "hold", "sell", "strongSell"))
        if atype == "stock" and has_analyst:
            sb   = details.get("strongBuy", 0)
            b    = details.get("buy", 0)
            hold = details.get("hold", 0)   # 'h' kullanma — html escape fn'i gölgeler
            sl   = details.get("sell", 0)
            ss   = details.get("strongSell", 0)
            total = sb + b + hold + sl + ss or 1
            segs = [
                ("Güçlü Al", sb,   "#3fb950"),
                ("Al",       b,    "#7cc96a"),
                ("Tut",      hold, "#c8a93f"),
                ("Sat",      sl,   "#e08641"),
                ("Güçlü Sat", ss,  "#f4554a"),
            ]
            bar = ""
            for label, val, col in segs:
                if val > 0:
                    bar += (f"<div class='analyst-seg' "
                            f"style='width:{val/total*100:.1f}%; background:{col};'>"
                            f"{val}</div>")
            legend = ""
            for label, val, col in segs:
                legend += (f"<div class='al-leg'>"
                           f"<span class='sw' style='background:{col};'></span>"
                           f"{label} <b class='mono' style='color:var(--tx);'>{val}</b></div>")
            body = (f"<div>"
                    f"<div class='analyst-bar'>{bar}</div>"
                    f"<div class='analyst-legend'>{legend}</div>"
                    f"<div class='muted tiny' style='margin-top:12px;'>"
                    f"{total} analist · son 30 gün konsensüsü</div>"
                    f"</div>")
        else:
            body = ("<div class='muted tiny' style='padding:8px 0;'>"
                    "Emtia ETF — kurumsal analist kapsamı yok. "
                    "Sinyal teknik + haber ağırlıklı üretilir.</div>")
        st.markdown(panel("Analist Konsensüsü", body, ico="rec"),
                    unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ────────────────────── Temel veriler ──────────────────────
    metrics = payload.get("raw_metrics", {}) or {}
    if atype == "stock":
        facts = [
            ("F/K",            fmt_x(metrics.get("peTTM") or metrics.get("peBasicExclExtraTTM"))),
            ("PD/DD",          fmt_x(metrics.get("pbQuarterly") or metrics.get("pbAnnual"))),
            ("P/S",            fmt_x(metrics.get("psTTM"))),
            ("ROE",            fmt_pct(metrics.get("roeTTM") or metrics.get("roeRfy"))),
            ("ROA",            fmt_pct(metrics.get("roaTTM") or metrics.get("roaRfy"))),
            ("Net Marj",       fmt_pct(metrics.get("netProfitMarginTTM"))),
            ("Brüt Marj",      fmt_pct(metrics.get("grossMarginTTM"))),
            ("Gelir Büyümesi", fmt_pct(metrics.get("revenueGrowthTTMYoy"))),
            ("EPS Büyümesi",   fmt_pct(metrics.get("epsGrowthTTMYoy"))),
            ("Cari Oran",      fmt_x(metrics.get("currentRatioQuarterly"))),
            ("Borç/Özkaynak",  fmt_x(metrics.get("totalDebt/totalEquityQuarterly"))),
            ("Beta",           fmt_num(metrics.get("beta"))),
            ("Temettü Verimi", fmt_pct(metrics.get("currentDividendYieldTTM"))),
            ("Piyasa Değeri",  fmt_cap(payload.get("market_cap"))),
        ]
        title = "Temel Finansal Veriler"
        note = "TTM · Finnhub"
    else:
        # ETF için teknik tabanlı veriler
        facts = [
            ("Beta",           fmt_num(metrics.get("beta"))),
            ("52H Yüksek",     fmt_price(metrics.get("52WeekHigh"))),
            ("52H Düşük",      fmt_price(metrics.get("52WeekLow"))),
            ("Hacim Oranı",    fmt_x(metrics.get("volumeQuarterly") or metrics.get("3MonthAverageTradingVolume"))),
        ]
        # Eksik kalan slotları doldurmak için 4 daha
        rets = (payload.get("returns") or {})
        facts += [
            ("3 Ay Getiri",    fmt_pct(rets.get("m3"))),
            ("1 Yıl Getiri",   fmt_pct(rets.get("y1"))),
            ("YBB Getiri",     fmt_pct(rets.get("ytd"))),
            ("1 Ay Getiri",    fmt_pct(rets.get("m1"))),
        ]
        title = "ETF / Teknik Veriler"
        note = "hesaplanan"

    # 4 sütun grid
    facts_html = ""
    for i, (k, v) in enumerate(facts):
        border = "" if (i % 4 == 3) else "border-right:1px solid var(--line-faint);"
        # Son satırın alt border'ını sil
        if i >= len(facts) - (len(facts) % 4 or 4):
            bottom = "border-bottom:none;"
        else:
            bottom = ""
        facts_html += (
            f"<div class='fact' style='{border}{bottom}'>"
            f"<span class='fact-k'>{k}</span>"
            f"<span class='fact-v'>{v}</span></div>"
        )
    body_html = (f"<div class='facts' style='grid-template-columns:repeat(4,1fr);'>"
                 f"{facts_html}</div>")
    st.markdown(
        panel(title, body_html, ico="doc",
              right=f"<span class='panel-note'>{note}</span>",
              pad=False, style="margin-bottom:16px;"),
        unsafe_allow_html=True,
    )

    # ────────────────────── Son haberler ──────────────────────
    news = db.recent_news(symbol, limit=8)
    if news:
        items_html = ""
        for n in news:
            sent_v = n.get("sentiment")
            sc = ("pos" if (sent_v or 0) > 0.08
                  else "neg" if (sent_v or 0) < -0.08 else "neu")
            sent_text = ("+" if (sent_v or 0) > 0 else "") + f"{(sent_v or 0):.2f}"
            published = (n.get("published_at") or "")[:10]
            time_part = (n.get("published_at") or "")[11:16]
            cat = n.get("category") or "—"
            items_html += (
                f"<div class='news-item'>"
                f"<div class='news-thumb'>"
                f"<span class='nt'>{symbol[:2]}</span>"
                f"</div>"
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
        # 2 sütunlu grid
        body = (f"<div class='grid' style='grid-template-columns:1fr 1fr; "
                f"gap:0 28px; padding:4px 16px 8px;'>{items_html}</div>")
        st.markdown(
            panel("Son Haberler", body, ico="news",
                  right="<span class='panel-note'>son 14 gün · VADER sentiment</span>",
                  pad=False),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            panel("Son Haberler",
                  "<div class='muted'>Bu sembol için kayıtlı haber yok</div>",
                  ico="news"),
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)  # .page
