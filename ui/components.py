"""
UI bileşenleri — Claude Design handoff bundle'ından port edildi.

Stil sistemi: IBM Plex Sans + Mono, elektrik mavi accent (#3b9eff), koyu tema.
CSS değişkenleri ve sınıf adları design dokümantasyonuyla birebir.
"""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st


# ---------------------------------------------------------------- #
# Palette — design system CSS değişkenleri
# ---------------------------------------------------------------- #
PALETTE = {
    # Yüzeyler (koyu → açık)
    "bg":        "#070a12",
    "bg_panel":  "#0f1320",
    "bg_elev":   "#161a2a",
    "bg_inset":  "#0a0d16",
    "line":      "#1e2333",
    "line_faint": "#161a28",
    # Metin (parlak → soluk)
    "tx_hi":     "#e6e9f2",
    "tx":        "#a4adc1",
    "tx_dim":    "#6e788f",
    "tx_faint":  "#525b73",
    # Aksiyon renkleri
    "accent":    "#3b9eff",
    "accent_d":  "#2e7fd6",
    "pos":       "#3fb950",
    "neg":       "#f4554a",
    "warn":      "#d4a83e",
    # Skor renkleri
    "score_hi":  "#3fb950",
    "score_mid": "#d4a83e",
    "score_lo":  "#f4554a",
    # Karar renkleri (analyst bar paletinden)
    "d_al":       "#3fb950",
    "d_biriktir": "#7cc96a",
    "d_tut":      "#c8a93f",
    "d_azalt":    "#e08641",
    "d_sat":      "#f4554a",
    # Köşe yuvarlama
    "r":         "10px",
    "r_lg":      "12px",
    "r_sm":      "6px",
}


def inject_css() -> None:
    """Tüm tasarım sistemini Streamlit'e enjekte eder. Sadece bir kez çağrılır.

    NOT: st.html() kullanılmalı, st.markdown() değil.
    Markdown parser CSS'teki [class*="x"] ve > karakterlerini link/blockquote
    olarak yorumlayıp <style> bloğunu bozuyor.
    """
    p = PALETTE
    st.html(f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
      :root {{
        --bg: {p['bg']};
        --bg-panel: {p['bg_panel']};
        --bg-elev: {p['bg_elev']};
        --bg-inset: {p['bg_inset']};
        --line: {p['line']};
        --line-faint: {p['line_faint']};
        --tx-hi: {p['tx_hi']};
        --tx: {p['tx']};
        --tx-dim: {p['tx_dim']};
        --tx-faint: {p['tx_faint']};
        --accent: {p['accent']};
        --pos: {p['pos']};
        --neg: {p['neg']};
        --warn: {p['warn']};
        --score-hi: {p['score_hi']};
        --score-mid: {p['score_mid']};
        --score-lo: {p['score_lo']};
        --d-al: {p['d_al']};
        --d-biriktir: {p['d_biriktir']};
        --d-tut: {p['d_tut']};
        --d-azalt: {p['d_azalt']};
        --d-sat: {p['d_sat']};
        --r: {p['r']};
        --r-lg: {p['r_lg']};
        --r-sm: {p['r_sm']};
        --f-sans: 'IBM Plex Sans', -apple-system, system-ui, sans-serif;
        --f-mono: 'IBM Plex Mono', ui-monospace, 'Courier New', monospace;
      }}

      /* ───────── Streamlit native overrides ───────── */
      html, body, [class*="css"] {{
        font-family: var(--f-sans) !important;
        -webkit-font-smoothing: antialiased;
      }}
      .stApp {{ background: var(--bg); color: var(--tx); }}
      .block-container {{
        padding: 1.2rem 1.6rem 4rem !important;
        max-width: 1400px;
      }}
      header[data-testid="stHeader"] {{ display: none; }}
      footer {{ display: none; }}
      #MainMenu {{ display: none; }}

      /* ───────── Sidebar ───────── */
      [data-testid="stSidebar"] {{
        background: var(--bg-panel) !important;
        border-right: 1px solid var(--line);
        padding-top: 0;
      }}
      [data-testid="stSidebar"] > div:first-child {{
        padding-top: 0.6rem;
      }}
      [data-testid="stSidebar"] [data-testid="stMarkdown"] {{
        color: var(--tx);
      }}
      /* Sidebar radio'yu nav item gibi göster */
      [data-testid="stSidebar"] [role="radiogroup"] {{
        gap: 2px;
      }}
      [data-testid="stSidebar"] [role="radiogroup"] > label {{
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 9px 12px;
        border-radius: 8px;
        cursor: pointer;
        margin: 0;
        transition: background .12s;
        color: var(--tx);
        font-size: 13.5px;
        font-weight: 500;
      }}
      [data-testid="stSidebar"] [role="radiogroup"] > label:hover {{
        background: var(--bg-elev);
        color: var(--tx-hi);
      }}
      [data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {{
        display: none;  /* radio dairesini gizle */
      }}
      [data-testid="stSidebar"] [role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) {{
        background: color-mix(in srgb, var(--accent) 18%, transparent);
        color: var(--tx-hi);
      }}
      /* Eski Chromium fallback: checked label için border-left */
      [data-testid="stSidebar"] [role="radiogroup"] > label > div:last-child {{
        color: inherit !important;
      }}

      /* Sidebar brand */
      .brand {{
        display: flex; align-items: center; gap: 11px;
        padding: 4px 12px 18px;
      }}
      .brand-mark {{
        width: 36px; height: 36px; border-radius: 9px;
        background: linear-gradient(135deg, var(--accent) 0%, #2e6fbf 100%);
        display: grid; place-items: center;
        box-shadow: 0 6px 18px rgba(59,158,255,.28);
      }}
      .brand-mark svg {{ width: 19px; height: 19px; }}
      .brand-name {{
        font-size: 14px; font-weight: 700;
        color: var(--tx-hi); letter-spacing: -0.005em;
      }}
      .brand-sub {{
        font-family: var(--f-mono);
        font-size: 10px; color: var(--tx-faint);
        letter-spacing: 0.06em; margin-top: 1px;
      }}
      .nav-label {{
        font-family: var(--f-mono);
        font-size: 10px; color: var(--tx-faint);
        text-transform: uppercase; letter-spacing: 0.12em;
        padding: 8px 12px 8px;
        font-weight: 600;
      }}

      /* Sidebar run butonu */
      [data-testid="stSidebar"] .stButton > button {{
        width: 100%;
        background: var(--accent) !important;
        color: white !important;
        border: 1px solid var(--accent) !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        padding: 9px 12px !important;
        border-radius: 8px !important;
        transition: filter .12s, transform .08s;
      }}
      [data-testid="stSidebar"] .stButton > button:hover {{
        filter: brightness(1.08);
      }}
      [data-testid="stSidebar"] .stButton > button:disabled {{
        background: var(--bg-elev) !important;
        color: var(--tx-dim) !important;
        border-color: var(--line) !important;
      }}
      .cron-status {{
        display: flex; align-items: center; gap: 8px;
        padding: 9px 12px;
        font-size: 11.5px; color: var(--tx-dim);
        margin-top: 6px;
      }}
      .dot {{
        width: 7px; height: 7px; border-radius: 50%;
        flex-shrink: 0;
      }}
      .dot.ok   {{ background: var(--pos);  box-shadow: 0 0 6px rgba(63,185,80,.5); }}
      .dot.warn {{ background: var(--warn); box-shadow: 0 0 6px rgba(212,168,62,.5); }}
      .dot.err  {{ background: var(--neg);  box-shadow: 0 0 6px rgba(244,85,74,.5); }}

      /* ───────── Page kabuğu ───────── */
      .page {{ animation: fade .25s ease-out; }}
      @keyframes fade {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: none; }} }}

      .page-head {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 24px;
        margin-bottom: 18px;
        flex-wrap: wrap;
      }}
      .page-title {{
        font-size: 22px; font-weight: 700;
        color: var(--tx-hi); letter-spacing: -0.015em;
        line-height: 1.2;
      }}
      .page-sub {{
        font-size: 12.5px; color: var(--tx-dim);
        margin-top: 3px;
      }}
      .page-meta {{
        display: flex; align-items: center; gap: 7px;
        font-size: 11.5px; color: var(--tx-dim);
        font-family: var(--f-mono);
      }}

      /* ───────── Panel ───────── */
      .panel {{
        background: var(--bg-panel);
        border: 1px solid var(--line);
        border-radius: var(--r-lg);
        overflow: visible;   /* Tablo yatay scroll için visible — clip sadece head'de */
      }}
      .panel-head {{
        display: flex; align-items: center; justify-content: space-between;
        padding: 12px 16px;
        border-bottom: 1px solid var(--line);
        background: linear-gradient(180deg, rgba(255,255,255,.015) 0%, transparent 100%);
        border-radius: var(--r-lg) var(--r-lg) 0 0;
        overflow: hidden;
      }}
      .panel-title {{
        display: flex; align-items: center; gap: 8px;
        font-size: 13px; font-weight: 600;
        color: var(--tx-hi); letter-spacing: -0.005em;
      }}
      .panel-title .ico {{
        color: var(--accent);
        display: inline-flex; align-items: center;
      }}
      .panel-title .ico svg {{ width: 15px; height: 15px; }}
      .panel-note {{
        font-family: var(--f-mono);
        font-size: 10.5px; color: var(--tx-faint);
        letter-spacing: 0.04em;
      }}
      .panel-body {{ padding: 14px 16px; }}

      /* Grid sistemi */
      .grid {{ display: grid; gap: 14px; }}

      /* Row/between helper */
      .row {{ display: flex; align-items: center; }}
      .between {{ justify-content: space-between; }}

      /* ───────── KPI ───────── */
      .kpi {{
        background: var(--bg-panel);
        border: 1px solid var(--line);
        border-radius: var(--r-lg);
        padding: 12px 14px;
        position: relative;
        overflow: hidden;
        min-width: 0;
      }}
      .kpi.kpi-accent::before {{
        content: ""; position: absolute;
        top: 0; left: 0; right: 0; height: 2px;
        background: var(--accent);
      }}
      .kpi-label {{
        font-family: var(--f-mono);
        font-size: 9.5px; color: var(--tx-faint);
        text-transform: uppercase; letter-spacing: 0.08em;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}
      .kpi-val {{
        font-family: var(--f-mono);
        font-size: 26px; font-weight: 600;
        color: var(--tx-hi); letter-spacing: -0.01em;
        line-height: 1.05; margin-top: 5px;
      }}
      .kpi-val .unit {{
        font-size: 13px; color: var(--tx-faint);
        font-weight: 500; margin-left: 2px;
      }}
      .kpi-foot {{
        font-size: 11px; margin-top: 6px;
        color: var(--tx-dim);
      }}

      /* ───────── Badges & chips ───────── */
      .badge {{
        display: inline-block;
        font-family: var(--f-mono);
        font-size: 9.5px; font-weight: 600;
        padding: 2px 6px; border-radius: 4px;
        letter-spacing: 0.06em; text-transform: uppercase;
      }}
      .badge.kind-stock {{ background: rgba(59,158,255,.14); color: var(--accent); }}
      .badge.kind-etf   {{ background: rgba(124,201,106,.14); color: var(--d-biriktir); }}
      .badge.badge-soft {{
        background: var(--bg-elev); color: var(--tx-dim);
        font-family: var(--f-sans); text-transform: none;
        font-size: 11px; padding: 2px 8px; letter-spacing: 0;
      }}

      /* Karar rozeti */
      .decision {{
        display: inline-block;
        font-size: 11px; font-weight: 700;
        padding: 3px 9px; border-radius: 5px;
        letter-spacing: 0.04em;
      }}
      .decision.AL       {{ background: rgba(63,185,80,.16);  color: var(--d-al); }}
      .decision.GÜÇLÜAL  {{ background: rgba(63,185,80,.22);  color: var(--d-al);
                            box-shadow: 0 0 0 1px rgba(63,185,80,.3); }}
      .decision.BİRİKTİR {{ background: rgba(124,201,106,.16); color: var(--d-biriktir); }}
      .decision.TUT      {{ background: rgba(200,169,63,.16); color: var(--d-tut); }}
      .decision.AZALT    {{ background: rgba(224,134,65,.16); color: var(--d-azalt); }}
      .decision.SAT      {{ background: rgba(244,85,74,.16);  color: var(--d-sat); }}
      .decision.GÜÇLÜSAT {{ background: rgba(244,85,74,.22);  color: var(--d-sat);
                            box-shadow: 0 0 0 1px rgba(244,85,74,.3); }}

      /* Değişim rozeti */
      .chg {{
        font-family: var(--f-mono);
        font-size: 12px; font-weight: 500;
      }}
      .chg.pos  {{ color: var(--pos); }}
      .chg.neg  {{ color: var(--neg); }}
      .chg.flat {{ color: var(--tx-dim); }}

      /* Sentiment chip */
      .sent-chip {{
        display: inline-flex; align-items: center; gap: 4px;
        font-family: var(--f-mono);
        font-size: 11px; font-weight: 500;
        padding: 2px 7px; border-radius: 4px;
      }}
      .sent-chip.pos {{ background: rgba(63,185,80,.14);  color: var(--pos); }}
      .sent-chip.neg {{ background: rgba(244,85,74,.14);  color: var(--neg); }}
      .sent-chip.neu {{ background: var(--bg-elev);       color: var(--tx-dim); }}

      .cat-chip {{
        display: inline-block;
        font-size: 10.5px; padding: 2px 7px; border-radius: 4px;
        background: var(--bg-elev); color: var(--tx-dim);
      }}

      /* ───────── Score bar / Dim row ───────── */
      .scorebar {{
        display: flex; align-items: center; gap: 9px;
      }}
      .scorebar-val {{
        font-family: var(--f-mono);
        font-size: 14px; font-weight: 600;
        min-width: 22px; text-align: right;
      }}
      .scorebar-track {{
        flex: 1; height: 6px; background: var(--bg-inset);
        border-radius: 3px; overflow: hidden;
      }}
      .scorebar-fill {{
        height: 100%; border-radius: 3px;
        transition: width .25s ease;
      }}

      .dim-row {{
        display: grid;
        grid-template-columns: 130px 1fr 32px;
        align-items: center; gap: 12px;
        padding: 7px 0;
      }}
      .dim-name {{
        font-size: 12.5px; color: var(--tx);
      }}
      .dim-track {{
        height: 6px; background: var(--bg-inset);
        border-radius: 3px; overflow: hidden;
      }}
      .dim-fill {{
        height: 100%; border-radius: 3px;
        transition: width .25s ease;
      }}
      .dim-val {{
        font-family: var(--f-mono);
        font-size: 13px; font-weight: 600;
        text-align: right;
      }}

      /* ───────── Tablo ───────── */
      .tbl-wrap {{ overflow-x: auto; }}
      .tbl {{
        width: 100%; border-collapse: collapse;
        font-size: 12.5px;
      }}
      .tbl thead th {{
        font-family: var(--f-mono);
        font-size: 9.5px; font-weight: 600;
        color: var(--tx-faint);
        text-transform: uppercase; letter-spacing: 0.06em;
        text-align: left;
        padding: 8px 10px;
        border-bottom: 1px solid var(--line);
        background: var(--bg-inset);
        white-space: nowrap;
      }}
      .tbl thead th.r {{ text-align: right; }}
      .tbl tbody tr {{
        cursor: pointer;
        transition: background .1s;
      }}
      .tbl tbody tr:hover {{ background: var(--bg-elev); }}
      .tbl tbody td {{
        padding: 9px 10px;
        border-bottom: 1px solid var(--line-faint);
        color: var(--tx);
        vertical-align: middle;
        white-space: nowrap;
      }}
      .tbl tbody td.r {{ text-align: right; }}
      .tbl .tk {{
        font-family: var(--f-mono);
        font-weight: 600;
        color: var(--tx-hi);
        font-size: 12.5px;
      }}
      .tbl .nm {{
        color: var(--tx-dim); font-size: 11.5px;
        margin-left: 6px;
      }}
      .tbl .mono {{ font-family: var(--f-mono); }}
      .tbl .hi {{ color: var(--tx-hi); }}

      /* ───────── Highlight cards (Top-3 / Top-5) ───────── */
      .hl-card {{
        background: var(--bg-panel);
        border: 1px solid var(--line);
        border-radius: var(--r-lg);
        padding: 14px 16px 16px;
        position: relative;
        cursor: pointer;
        transition: border-color .12s, transform .08s;
        display: flex; flex-direction: column; gap: 10px;
        min-height: 100%;
      }}
      .hl-card:hover {{
        border-color: var(--accent);
      }}
      .hl-rank {{
        position: absolute; top: 12px; right: 16px;
        font-family: var(--f-mono);
        font-size: 10px; font-weight: 700;
        color: var(--tx-faint); letter-spacing: 0.08em;
      }}
      .hl-top {{
        display: flex; align-items: center; gap: 9px;
      }}
      .hl-tk {{
        font-family: var(--f-mono);
        font-size: 18px; font-weight: 700;
        color: var(--tx-hi); letter-spacing: -0.005em;
      }}
      .hl-score-big {{
        font-family: var(--f-mono);
        font-size: 36px; font-weight: 700;
        letter-spacing: -0.025em; line-height: 1;
      }}

      /* ───────── Hero band (Detail page) ───────── */
      .statline {{
        display: flex; gap: 28px; flex-wrap: wrap;
      }}
      .stat {{
        display: flex; flex-direction: column; gap: 3px;
      }}
      .stat-k {{
        font-family: var(--f-mono);
        font-size: 10px; color: var(--tx-faint);
        text-transform: uppercase; letter-spacing: 0.1em;
        font-weight: 600;
      }}
      .stat-v {{
        font-family: var(--f-mono);
        font-size: 22px; font-weight: 600;
        color: var(--tx-hi); letter-spacing: -0.01em;
      }}

      /* ───────── Segmented toggle (Fiyat/Skor) ───────── */
      .seg {{
        display: inline-flex;
        background: var(--bg-inset);
        border-radius: 7px;
        padding: 3px;
        gap: 0;
      }}
      .seg button {{
        background: transparent; border: 0;
        padding: 5px 12px; border-radius: 5px;
        color: var(--tx-dim);
        font-family: var(--f-sans); font-size: 11.5px; font-weight: 500;
        cursor: pointer;
        transition: background .12s, color .12s;
      }}
      .seg button.on {{
        background: var(--bg-elev);
        color: var(--tx-hi);
      }}

      /* ───────── Back button (Detail) ───────── */
      .backbtn {{
        display: inline-flex; align-items: center; gap: 6px;
        background: var(--bg-elev);
        color: var(--tx);
        border: 1px solid var(--line);
        padding: 8px 12px;
        border-radius: 7px;
        font-size: 12.5px; font-weight: 500;
        cursor: pointer;
        transition: background .12s, color .12s;
      }}
      .backbtn:hover {{ background: var(--line); color: var(--tx-hi); }}
      .backbtn svg {{ width: 13px; height: 13px; }}

      /* ───────── Bull / Bear case ───────── */
      .case-col {{
        padding: 14px 18px;
      }}
      .case-head {{
        display: flex; align-items: center; gap: 6px;
        font-size: 11px; font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 10px;
      }}
      .case-head.bull {{ color: var(--pos); }}
      .case-head.bear {{ color: var(--neg); }}
      .case-list {{
        list-style: none; margin: 0; padding: 0;
      }}
      .case-list li {{
        font-size: 12.5px; color: var(--tx);
        padding: 6px 0 6px 13px;
        line-height: 1.45;
        position: relative;
      }}
      .case-list li::before {{
        content: "›";
        position: absolute; left: 0;
        font-family: var(--f-mono);
        font-weight: 700;
      }}
      .case-list.bull li::before {{ color: var(--pos); }}
      .case-list.bear li::before {{ color: var(--neg); }}

      /* ───────── 52 hafta bandı ───────── */
      .band {{ padding: 8px 0 4px; }}
      .band-track {{
        position: relative;
        height: 6px;
        background: var(--bg-inset);
        border-radius: 3px;
        overflow: visible;
      }}
      .band-fill {{
        position: absolute; top: 0; left: 0; bottom: 0;
        background: linear-gradient(90deg, var(--neg) 0%, var(--warn) 50%, var(--pos) 100%);
        border-radius: 3px;
      }}
      .band-marker {{
        position: absolute;
        top: -3px; width: 2px; height: 12px;
        background: var(--tx-hi);
        transform: translateX(-50%);
        border-radius: 1px;
      }}
      .band-marker::after {{
        content: attr(data-v);
        position: absolute;
        top: -22px; left: 50%; transform: translateX(-50%);
        font-family: var(--f-mono);
        font-size: 11px; font-weight: 600;
        color: var(--tx-hi);
        white-space: nowrap;
      }}
      .band-ends {{
        display: flex; justify-content: space-between;
        margin-top: 14px;
        font-size: 11.5px; color: var(--tx-dim);
      }}
      .band-ends b {{
        font-family: var(--f-mono);
        color: var(--tx); font-weight: 600;
      }}

      /* ───────── Analist konsensüs bar ───────── */
      .analyst-bar {{
        display: flex; height: 26px;
        border-radius: 6px; overflow: hidden;
        margin-bottom: 12px;
      }}
      .analyst-seg {{
        display: grid; place-items: center;
        color: rgba(0,0,0,.7);
        font-family: var(--f-mono);
        font-size: 11px; font-weight: 700;
        min-width: 0;
      }}
      .analyst-legend {{
        display: flex; flex-wrap: wrap; gap: 10px 16px;
        font-size: 11.5px; color: var(--tx-dim);
      }}
      .al-leg {{ display: flex; align-items: center; gap: 6px; }}
      .sw {{
        width: 10px; height: 10px; border-radius: 2px;
        display: inline-block;
      }}

      /* ───────── Facts grid (temel veriler) ───────── */
      .facts {{
        display: grid;
      }}
      .fact {{
        padding: 12px 16px;
        border-bottom: 1px solid var(--line-faint);
        display: flex; flex-direction: column; gap: 4px;
      }}
      .fact-k {{
        font-family: var(--f-mono);
        font-size: 10px; color: var(--tx-faint);
        text-transform: uppercase; letter-spacing: 0.08em;
        font-weight: 600;
      }}
      .fact-v {{
        font-family: var(--f-mono);
        font-size: 14px; font-weight: 600;
        color: var(--tx-hi);
      }}

      /* ───────── Haber satırı ───────── */
      .news-item {{
        display: flex; gap: 12px;
        padding: 11px 0;
        border-bottom: 1px solid var(--line-faint);
      }}
      .news-item:last-child {{ border-bottom: none; }}
      .news-thumb {{
        width: 38px; height: 38px; flex-shrink: 0;
        border-radius: 7px;
        background: var(--bg-elev);
        display: grid; place-items: center;
      }}
      .news-thumb .nt {{
        font-family: var(--f-mono);
        font-size: 10px; font-weight: 700;
        color: var(--tx-dim); letter-spacing: 0.04em;
      }}
      .news-body {{ flex: 1; min-width: 0; }}
      .news-title {{
        font-size: 12.5px; font-weight: 500;
        color: var(--tx-hi); line-height: 1.4;
        margin-bottom: 4px;
      }}
      .news-title a {{ color: var(--tx-hi); text-decoration: none; }}
      .news-title a:hover {{ color: var(--accent); }}
      .news-meta {{
        font-family: var(--f-mono);
        font-size: 10.5px; color: var(--tx-faint);
        display: flex; gap: 6px; align-items: center;
        margin-bottom: 5px;
      }}
      .news-meta .sep {{ color: var(--tx-faint); }}
      .news-chips {{ display: flex; gap: 5px; }}

      /* ───────── Form inputs ───────── */
      .input {{
        background: var(--bg-inset);
        border: 1px solid var(--line);
        border-radius: 7px;
        color: var(--tx-hi);
        font-family: var(--f-sans);
        font-size: 12.5px;
        padding: 7px 10px;
        outline: none;
        transition: border-color .12s;
      }}
      .input:focus {{ border-color: var(--accent); }}
      select.input {{
        appearance: none;
        background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3e%3cpath fill='%237e8aa8' d='M0 0h10L5 6z'/%3e%3c/svg%3e");
        background-repeat: no-repeat;
        background-position: right 10px center;
        padding-right: 24px;
      }}

      /* Streamlit selectbox / multiselect uyumu */
      [data-baseweb="select"] > div {{
        background-color: var(--bg-inset) !important;
        border-color: var(--line) !important;
        color: var(--tx-hi) !important;
      }}
      [data-baseweb="input"] > div,
      .stTextInput input,
      .stTextArea textarea {{
        background-color: var(--bg-inset) !important;
        border-color: var(--line) !important;
        color: var(--tx-hi) !important;
        font-family: var(--f-sans);
      }}

      /* Streamlit dataframe theme */
      [data-testid="stDataFrame"] {{
        background: var(--bg-panel);
        border: 1px solid var(--line);
        border-radius: var(--r-lg);
      }}

      /* ───────── Chip filter (haberler) ───────── */
      .chips-multi {{
        display: flex; flex-wrap: wrap; gap: 6px;
      }}
      .chip-sel {{
        padding: 5px 10px;
        background: var(--bg-inset);
        border: 1px solid var(--line);
        border-radius: 6px;
        font-size: 11.5px;
        color: var(--tx-dim);
        cursor: pointer;
        user-select: none;
        transition: all .12s;
      }}
      .chip-sel.mono {{ font-family: var(--f-mono); font-weight: 500; }}
      .chip-sel:hover {{ color: var(--tx-hi); border-color: var(--line); }}
      .chip-sel.on {{
        background: rgba(59,158,255,.12);
        border-color: var(--accent);
        color: var(--accent);
      }}

      .sectionlabel {{
        font-family: var(--f-mono);
        font-size: 10px; color: var(--tx-faint);
        text-transform: uppercase; letter-spacing: 0.1em;
        font-weight: 600;
        margin-bottom: 7px;
      }}

      .toggle {{
        width: 32px; height: 18px;
        background: var(--bg-elev);
        border-radius: 999px;
        cursor: pointer;
        position: relative;
        transition: background .15s;
      }}
      .toggle::after {{
        content: "";
        position: absolute;
        top: 2px; left: 2px;
        width: 14px; height: 14px; border-radius: 50%;
        background: var(--tx-dim);
        transition: transform .15s, background .15s;
      }}
      .toggle.on {{ background: var(--accent); }}
      .toggle.on::after {{
        transform: translateX(14px);
        background: white;
      }}

      /* ───────── Misc text helpers ───────── */
      .muted {{ color: var(--tx-dim); }}
      .faint {{ color: var(--tx-faint); }}
      .tiny  {{ font-size: 10.5px; }}
      .mono  {{ font-family: var(--f-mono); }}
      .hi    {{ color: var(--tx-hi); }}

      /* Disclaimer */
      .disclaimer {{
        font-size: 10.5px; color: var(--tx-faint);
        background: var(--bg-inset);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 10px 14px;
        margin-top: 18px;
        font-family: var(--f-mono);
        line-height: 1.55;
      }}

      /* ───────── Ana içerik butonları (nav, export) ───────── */
      [data-testid="stMain"] .stButton > button {{
        background: var(--bg-elev) !important;
        color: var(--tx) !important;
        border: 1px solid var(--line) !important;
        font-size: 12px !important;
        padding: 7px 10px !important;
        border-radius: 7px !important;
        font-family: var(--f-sans) !important;
        font-weight: 500 !important;
        transition: all .12s;
      }}
      [data-testid="stMain"] .stButton > button:hover {{
        background: rgba(59,158,255,.1) !important;
        color: var(--accent) !important;
        border-color: var(--accent) !important;
      }}
      /* Download butonu */
      [data-testid="stMain"] [data-testid="stDownloadButton"] button {{
        background: var(--bg-elev) !important;
        color: var(--tx-dim) !important;
        border: 1px solid var(--line) !important;
        font-size: 11.5px !important;
        font-family: var(--f-mono) !important;
        padding: 6px 12px !important;
        border-radius: 7px !important;
        transition: all .12s;
      }}
      [data-testid="stMain"] [data-testid="stDownloadButton"] button:hover {{
        color: var(--tx-hi) !important;
        border-color: var(--tx-dim) !important;
      }}
    </style>
    """)


# ---------------------------------------------------------------- #
# Güvenlik: HTML escape
# ---------------------------------------------------------------- #
def h(text: str | None) -> str:
    """HTML özel karakterlerini escape et — XSS koruması için."""
    if not text:
        return ""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;"))


# ---------------------------------------------------------------- #
# Renk & biçimlendirme yardımcıları (ui.jsx birebir)
# ---------------------------------------------------------------- #
def score_color(v: int | float | None) -> str:
    """Skoru CSS değişkenine eşle (ui.jsx scoreColor karşılığı)."""
    if v is None:
        return PALETTE["tx_dim"]
    if v >= 67: return PALETTE["score_hi"]
    if v >= 50: return PALETTE["score_mid"]
    if v >= 38: return PALETTE["d_azalt"]
    return PALETTE["score_lo"]


def sent_class(v: float | None) -> str:
    """Sentiment chip sınıfı."""
    if v is None: return "neu"
    if v > 0.08: return "pos"
    if v < -0.08: return "neg"
    return "neu"


def sent_label(v: float | None) -> str:
    if v is None: return "—"
    return ("+" if v > 0 else "") + f"{v:.2f}"


def fmt_chg_class(v: float | None) -> str:
    if v is None: return "flat"
    if v > 0.01: return "pos"
    if v < -0.01: return "neg"
    return "flat"


def fmt_chg_str(v: float | None) -> str:
    if v is None: return "—"
    return ("+" if v > 0 else "") + f"{v:.2f}%"


def fmt_price(v: float | None) -> str:
    if v is None: return "—"
    return f"${v:,.2f}"


def fmt_num(v: float | None, decimals: int = 2) -> str:
    if v is None: return "—"
    return f"{v:,.{decimals}f}"


def fmt_pct(v: float | None) -> str:
    if v is None: return "—"
    return ("+" if v > 0 else "") + f"{v:.1f}%"


def fmt_x(v: float | None) -> str:
    if v is None: return "—"
    return f"{v:.2f}"


def fmt_cap(v: float | None) -> str:
    if v is None: return "—"
    if v >= 1e6: return f"${v/1e6:.2f}T"
    if v >= 1e3: return f"${v/1e3:.2f}B"
    return f"${v:.0f}M"


# ---------------------------------------------------------------- #
# İkonlar (SVG inline — ui.jsx Ic objesinin Python karşılığı)
# ---------------------------------------------------------------- #
def _svg(d: str, w: int = 16) -> str:
    """Stroke ikonu sarmal."""
    return (f"<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' "
            f"stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round' "
            f"width='{w}' height='{w}'>{d}</svg>")


def icon(name: str, w: int = 16) -> str:
    paths = {
        "overview": "<rect x='3' y='3' width='7' height='9' rx='1.5'/><rect x='14' y='3' width='7' height='5' rx='1.5'/><rect x='14' y='12' width='7' height='9' rx='1.5'/><rect x='3' y='16' width='7' height='5' rx='1.5'/>",
        "detail":   "<path d='M3 17l5-6 4 3 5-7'/><path d='M16 7h4v4'/><path d='M3 21h18'/>",
        "news":     "<path d='M4 5h13v14H6a2 2 0 0 1-2-2V5z'/><path d='M17 8h2a1 1 0 0 1 1 1v8a2 2 0 0 1-2 2'/><path d='M7 9h7M7 13h7M7 17h4'/>",
        "rec":      "<path d='M9 18h6'/><path d='M10 21h4'/><path d='M12 3a6 6 0 0 0-4 10.5c.6.6 1 1.3 1 2.1V16h6v-.4c0-.8.4-1.5 1-2.1A6 6 0 0 0 12 3z'/>",
        "settings": "<circle cx='12' cy='12' r='3'/><path d='M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1A1.6 1.6 0 0 0 8.3 19a1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1A1.6 1.6 0 0 0 5 8.3a1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9a1.6 1.6 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9a1.6 1.6 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z'/>",
        "refresh":  "<path d='M3 12a9 9 0 0 1 15-6.7L21 8'/><path d='M21 3v5h-5'/><path d='M21 12a9 9 0 0 1-15 6.7L3 16'/><path d='M3 21v-5h5'/>",
        "arrowUp":  "<path d='M12 19V5M5 12l7-7 7 7'/>",
        "arrowDown":"<path d='M12 5v14M19 12l-7 7-7-7'/>",
        "back":     "<path d='M15 18l-6-6 6-6'/>",
        "bell":     "<path d='M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9'/><path d='M13.7 21a2 2 0 0 1-3.4 0'/>",
        "flame":    "<path d='M12 2s4 4 4 8a4 4 0 0 1-8 0c0-1 .5-2 1-3 0 1.5 1 2 1.5 2 0-2-1-3 1.5-7z'/><path d='M8.5 14a3.5 3.5 0 0 0 7 0c0-2-1.5-3-1.5-3'/>",
        "gauge":    "<path d='M12 14l4-4'/><path d='M3.5 17a9 9 0 1 1 17 0'/><circle cx='12' cy='14' r='1.4' fill='currentColor' stroke='none'/>",
        "layers":   "<path d='M12 3l9 5-9 5-9-5 9-5z'/><path d='M3 13l9 5 9-5'/>",
        "doc":      "<path d='M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z'/><path d='M14 3v5h5'/><path d='M9 13h6M9 17h6'/>",
        "search":   "<circle cx='11' cy='11' r='7'/><path d='M21 21l-4-4'/>",
        "filter":   "<path d='M3 5h18l-7 8v6l-4-2v-4z'/>",
        "key":      "<circle cx='8' cy='15' r='4'/><path d='M10.8 12.2L20 3M16 7l3 3M14 9l2 2'/>",
        "clock":    "<circle cx='12' cy='12' r='9'/><path d='M12 7v5l3 2'/>",
        "list":     "<path d='M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01'/>",
        "brand":    "<path d='M3 17l5-6 4 3 5-8'/><path d='M3 21h18'/>",
        "database": "<ellipse cx='12' cy='5' rx='9' ry='3'/><path d='M21 12c0 1.66-4 3-9 3s-9-1.34-9-3'/><path d='M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5'/>",
        "trash":    "<polyline points='3 6 5 6 21 6'/><path d='M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6'/><path d='M10 11v6M14 11v6'/><path d='M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2'/>",
    }
    return _svg(paths.get(name, ""), w=w)


# ---------------------------------------------------------------- #
# HTML helper'lar (ui.jsx React komponentleri → Python string'i)
# ---------------------------------------------------------------- #
def page_head(title: str, sub: str = "", meta: str = "",
              meta_status: str = "ok") -> str:
    """Sayfa başlığı bloğu — her sayfanın tepesinde."""
    meta_html = ""
    if meta:
        meta_html = (f"<div class='page-meta'>"
                     f"<span class='dot {meta_status}'></span>{meta}</div>")
    return (f"<div class='page-head'>"
            f"<div>"
            f"<div class='page-title'>{title}</div>"
            f"<div class='page-sub'>{sub}</div>"
            f"</div>{meta_html}</div>")


def panel_open(title: str = "", ico: str = "", right: str = "",
               style: str = "", cls: str = "") -> str:
    """Panel açılışı — body içine st.markdown ile içerik yaz, sonra panel_close()."""
    head = ""
    if title or right:
        ico_html = (f"<span class='ico'>{icon(ico)}</span>" if ico else "")
        head = (f"<div class='panel-head'>"
                f"<div class='panel-title'>{ico_html}{title}</div>"
                f"{right}</div>")
    style_attr = f"style='{style}'" if style else ""
    return f"<div class='panel {cls}' {style_attr}>{head}<div class='panel-body'>"


def panel_close() -> str:
    return "</div></div>"


def panel(title: str, body_html: str, ico: str = "", right: str = "",
          style: str = "", pad: bool = True) -> str:
    """Komple panel — body_html zaten hazır HTML."""
    head_html = ""
    if title or right:
        ico_html = (f"<span class='ico'>{icon(ico)}</span>" if ico else "")
        head_html = (f"<div class='panel-head'>"
                     f"<div class='panel-title'>{ico_html}{title}</div>"
                     f"{right}</div>")
    style_attr = f"style='{style}'" if style else ""
    body = f"<div class='panel-body'>{body_html}</div>" if pad else body_html
    return f"<div class='panel' {style_attr}>{head_html}{body}</div>"


def kpi(label: str, value: str, unit: str = "",
        foot: str = "", color: str | None = None,
        accent: bool = False) -> str:
    """KPI kart HTML'i (st.markdown ile satır içinde)."""
    cls = "kpi" + (" kpi-accent" if accent else "")
    color_style = f"style='color:{color}'" if color else ""
    unit_html = f"<span class='unit'>{unit}</span>" if unit else ""
    foot_html = f"<div class='kpi-foot'>{foot}</div>" if foot else ""
    return (f"<div class='{cls}'>"
            f"<div class='kpi-label'>{label}</div>"
            f"<div class='kpi-val' {color_style}>{value}{unit_html}</div>"
            f"{foot_html}</div>")


def kind_badge(kind: str) -> str:
    """HİSSE / ETF rozet."""
    if kind == "stock":
        return "<span class='badge kind-stock'>HİSSE</span>"
    return "<span class='badge kind-etf'>ETF</span>"


def decision_badge(d: str | None, big: bool = False) -> str:
    if not d:
        return "<span class='decision' style='background:var(--bg-elev);color:var(--tx-dim)'>—</span>"
    # "GÜÇLÜ AL" → "GÜÇLÜAL" (boşluk CSS class ayırır, stil bozulurdu)
    safe = d.replace(" ", "")
    style = " style='font-size:13px;padding:5px 12px'" if big else ""
    return f"<span class='decision {safe}'{style}>{d}</span>"


def chg_badge(v: float | None, with_icon: bool = False) -> str:
    cls = fmt_chg_class(v)
    s = fmt_chg_str(v)
    arrow = ""
    if with_icon and cls in ("pos", "neg"):
        arrow = "▲ " if cls == "pos" else "▼ "
    return f"<span class='chg {cls}'>{arrow}{s}</span>"


def sent_chip(v: float | None) -> str:
    return f"<span class='sent-chip {sent_class(v)}'>{sent_label(v)}</span>"


def score_bar(v: int | None) -> str:
    if v is None:
        return "<span class='muted tiny'>—</span>"
    col = score_color(v)
    return (f"<div class='scorebar'>"
            f"<span class='scorebar-val' style='color:{col}'>{v}</span>"
            f"<div class='scorebar-track'>"
            f"<div class='scorebar-fill' style='width:{v}%;background:{col}'></div>"
            f"</div></div>")


def dim_bar(name: str, value: int | None) -> str:
    if value is None:
        return (f"<div class='dim-row'>"
                f"<div class='dim-name'>{name}</div>"
                f"<div class='dim-track'></div>"
                f"<div class='dim-val muted'>—</div></div>")
    col = score_color(value)
    return (f"<div class='dim-row'>"
            f"<div class='dim-name'>{name}</div>"
            f"<div class='dim-track'>"
            f"<div class='dim-fill' style='width:{value}%;background:{col}'></div>"
            f"</div>"
            f"<div class='dim-val' style='color:{col}'>{value}</div></div>")


def disclaimer_box() -> str:
    return ("<div class='disclaimer'>⚠ Kural tabanlı hesaplama · "
            "Geçmiş performans gelecek getirisini garanti etmez · "
            "Yatırım tavsiyesi DEĞİLDİR.</div>")


def spark_svg(values: list[float], color: str | None = None,
              w: int = 80, h: int = 28) -> str:
    """Saf SVG mini sparkline — tablo hücrelerine gömülebilir, Plotly gerekmez."""
    if not values or len(values) < 2:
        return f"<svg width='{w}' height='{h}'><line x1='0' y1='{h//2}' x2='{w}' y2='{h//2}' stroke='var(--line)' stroke-width='1'/></svg>"

    vmin, vmax = min(values), max(values)
    vrange = vmax - vmin or (abs(vmin) * 0.01) or 1

    # Renk: son değer ilk değerden yüksekse yeşil, değilse kırmızı
    if color is None:
        color = PALETTE["pos"] if values[-1] >= values[0] else PALETTE["neg"]

    margin_y = 3
    usable_h = h - margin_y * 2

    def to_xy(i: int, v: float) -> tuple[float, float]:
        x = (i / (len(values) - 1)) * w
        y = margin_y + usable_h - ((v - vmin) / vrange * usable_h)
        return round(x, 1), round(y, 1)

    pts = [to_xy(i, v) for i, v in enumerate(values)]
    line_pts = " ".join(f"{x},{y}" for x, y in pts)

    # Alan dolgu: sol alt → tüm noktalar → sağ alt
    area_pts = (f"0,{h} " +
                " ".join(f"{x},{y}" for x, y in pts) +
                f" {w},{h}")

    # Hex rengi rgba'ya çevir (fillColor için)
    fill_color = color

    return (
        f"<svg width='{w}' height='{h}' viewBox='0 0 {w} {h}' "
        f"style='display:block; overflow:visible;'>"
        f"<polygon points='{area_pts}' fill='{fill_color}' opacity='0.15'/>"
        f"<polyline points='{line_pts}' stroke='{fill_color}' "
        f"stroke-width='1.5' fill='none' stroke-linejoin='round'/>"
        f"</svg>"
    )


# ---------------------------------------------------------------- #
# Plotly grafikleri — design AreaChart estetiğinde
# ---------------------------------------------------------------- #
def area_chart(times: list, values: list[float],
               color: str | None = None,
               y_prefix: str = "$",
               height: int = 230) -> go.Figure:
    """Tek renk alan dolgulu çizgi grafiği — IBM Plex Mono eksenler."""
    if not values:
        return _empty_fig("Veri yok", height)
    col = color or PALETTE["accent"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=values, mode="lines", fill="tozeroy",
        line=dict(color=col, width=1.8, shape="linear"),
        fillcolor=_with_alpha(col, 0.22),
        hovertemplate=f"<b>%{{x|%d %b}}</b><br>{y_prefix}%{{y:,.2f}}<extra></extra>",
    ))
    # Son nokta vurgu
    if values:
        fig.add_trace(go.Scatter(
            x=[times[-1]], y=[values[-1]], mode="markers",
            marker=dict(size=8, color=col,
                        line=dict(color=PALETTE["bg_panel"], width=2)),
            hoverinfo="skip", showlegend=False,
        ))
    fig.update_layout(
        height=height, margin=dict(l=46, r=12, t=12, b=22),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=PALETTE["tx_dim"], family="IBM Plex Mono, monospace",
                  size=10),
        xaxis=dict(
            showgrid=False, showline=False, zeroline=False,
            tickfont=dict(size=10, color=PALETTE["tx_faint"]),
            tickformat="",
        ),
        yaxis=dict(
            showgrid=True, gridcolor=PALETTE["line_faint"], gridwidth=1,
            showline=False, zeroline=False,
            tickfont=dict(size=10, color=PALETTE["tx_faint"]),
            tickformat=",.0f",
            ticksuffix="",
            tickprefix=y_prefix,
        ),
        showlegend=False,
    )
    # Sol-alt ve sağ-alt anotasyonu (90g önce / bugün)
    fig.add_annotation(
        text="90g önce", xref="paper", yref="paper",
        x=0, y=-0.10, showarrow=False, xanchor="left",
        font=dict(size=10, family="IBM Plex Mono",
                  color=PALETTE["tx_faint"]),
    )
    fig.add_annotation(
        text="bugün", xref="paper", yref="paper",
        x=1, y=-0.10, showarrow=False, xanchor="right",
        font=dict(size=10, family="IBM Plex Mono",
                  color=PALETTE["tx_faint"]),
    )
    return fig


def sentiment_donut(pos: int, neu: int, neg: int) -> go.Figure:
    total = pos + neu + neg
    if total == 0:
        return _empty_fig("Haber yok", 200)
    fig = go.Figure(go.Pie(
        labels=["Pozitif", "Nötr", "Negatif"],
        values=[pos, neu, neg], hole=0.66,
        marker=dict(colors=[PALETTE["pos"], PALETTE["tx_dim"], PALETTE["neg"]],
                    line=dict(color=PALETTE["bg_panel"], width=3)),
        textinfo="none",
        hovertemplate="<b>%{label}</b>: %{value} (%{percent})<extra></extra>",
        sort=False, direction="clockwise",
    ))
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:10px;color:{PALETTE['tx_faint']}'>haber</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=22, family="IBM Plex Mono",
                  color=PALETTE["tx_hi"]),
    )
    fig.update_layout(
        height=200, margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


def _with_alpha(hex_color: str, alpha: float) -> str:
    """#RRGGBB → rgba(..., alpha)."""
    if hex_color.startswith("#") and len(hex_color) == 7:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        return f"rgba({r},{g},{b},{alpha})"
    return hex_color


def _empty_fig(msg: str, height: int = 220) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False,
                       font=dict(color=PALETTE["tx_faint"], size=12,
                                 family="IBM Plex Mono"))
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig
