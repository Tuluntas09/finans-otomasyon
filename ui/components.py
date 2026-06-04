"""
Yeniden kullanılabilir UI bileşenleri.

Streamlit'in built-in widget'ları yeterince güzel değil — burada plotly
ve özel HTML/CSS ile daha rafine bir görünüm üretiyoruz. Tüm renkler
mevcut "Hisse Analiz Motoru" projendeki paletle uyumlu.
"""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

# Palette — frontend projenle birebir
PALETTE = {
    "bg":      "#0a0e17",
    "panel":   "#121826",
    "panel2":  "#1a2234",
    "border":  "#232c40",
    "text":    "#e6ecf5",
    "muted":   "#8a96ad",
    "accent":  "#4f8cff",
    "green":   "#2ecc71",
    "green_d": "#1f9d57",
    "red":     "#ff5c6c",
    "orange":  "#ff8a5c",
    "yellow":  "#f5b942",
}


def inject_css() -> None:
    """Streamlit'in default temasını minimalist koyu temayla override eder."""
    st.markdown(f"""
    <style>
      .stApp {{
        background: radial-gradient(1200px 600px at 80% -10%, #16213a 0%, {PALETTE['bg']} 55%);
        color: {PALETTE['text']};
      }}
      .block-container {{ padding-top: 1.5rem; max-width: 1280px; }}
      [data-testid="stSidebar"] {{ background: {PALETTE['panel']}; }}
      [data-testid="stSidebar"] * {{ color: {PALETTE['text']} !important; }}
      .stMetric {{ background: {PALETTE['panel']}; padding: 12px 16px;
                   border: 1px solid {PALETTE['border']}; border-radius: 12px; }}
      div[data-testid="stMetricValue"] {{ font-size: 22px; color: {PALETTE['text']}; }}
      div[data-testid="stMetricLabel"] {{ color: {PALETTE['muted']}; }}

      .fcard {{
        background: {PALETTE['panel']}; border: 1px solid {PALETTE['border']};
        border-radius: 14px; padding: 18px; margin-bottom: 16px;
        box-shadow: 0 10px 40px rgba(0,0,0,.35);
      }}
      .fcard h3 {{ font-size: 13px; text-transform: uppercase;
                   letter-spacing: .8px; color: {PALETTE['muted']};
                   margin-bottom: 12px; font-weight: 700; }}
      .badge {{
        display: inline-block; padding: 4px 12px; border-radius: 999px;
        font-weight: 700; font-size: 13px; letter-spacing: .3px;
      }}
      .chg-up   {{ color: {PALETTE['green']}; background: rgba(46,204,113,.12);
                   padding: 2px 8px; border-radius: 6px; font-weight: 700; }}
      .chg-down {{ color: {PALETTE['red']};   background: rgba(255,92,108,.12);
                   padding: 2px 8px; border-radius: 6px; font-weight: 700; }}
      .news-item {{ display: flex; gap: 12px; padding: 12px 0;
                    border-bottom: 1px solid {PALETTE['border']}; }}
      .news-title {{ font-size: 14px; font-weight: 600;
                     color: {PALETTE['text']}; line-height: 1.35; }}
      .news-meta {{ color: {PALETTE['muted']}; font-size: 12px; margin-top: 4px; }}
      .pill {{ display: inline-block; padding: 2px 8px; border-radius: 6px;
              font-size: 11px; font-weight: 700; }}
      a {{ color: {PALETTE['accent']}; text-decoration: none; }}
      a:hover {{ text-decoration: underline; }}
    </style>
    """, unsafe_allow_html=True)


def score_ring(score: int | None, color: str, label: str, size: int = 220) -> go.Figure:
    """Plotly gauge — analiz skoru için merkez halka."""
    val = score if score is not None else 0
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val,
        number={
            "suffix": "<span style='font-size:13px;color:#8a96ad'>/100</span>",
            "font": {"size": 44, "color": color, "family": "Inter"},
        },
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "#232c40"},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "#1a2234",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  32],  "color": "rgba(255,92,108,.18)"},
                {"range": [32, 45],  "color": "rgba(255,138,92,.18)"},
                {"range": [45, 60],  "color": "rgba(245,185,66,.18)"},
                {"range": [60, 75],  "color": "rgba(46,204,113,.18)"},
                {"range": [75, 100], "color": "rgba(31,157,87,.25)"},
            ],
        },
        title={
            "text": f"<span style='font-size:12px;color:#8a96ad'>{label.upper()}</span>",
            "font": {"size": 12, "color": "#8a96ad"},
        },
        domain={"x": [0, 1], "y": [0, 1]},
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
        height=size,
        font=dict(color=PALETTE["text"], family="Inter"),
    )
    return fig


def dim_bar_chart(dimensions: list[Any]) -> go.Figure:
    """Boyut bazlı skor — yatay bar."""
    rows = [(d.name, d.score or 0, d.score is None) for d in dimensions]
    names = [r[0] for r in rows]
    scores = [r[1] for r in rows]
    colors = []
    for d in dimensions:
        sc = d.score
        if sc is None:        colors.append(PALETTE["muted"])
        elif sc >= 75:        colors.append(PALETTE["green_d"])
        elif sc >= 60:        colors.append(PALETTE["green"])
        elif sc >= 45:        colors.append(PALETTE["yellow"])
        elif sc >= 32:        colors.append(PALETTE["orange"])
        else:                 colors.append(PALETTE["red"])

    fig = go.Figure(go.Bar(
        x=scores, y=names, orientation="h",
        marker_color=colors,
        text=[f"{d.score}" if d.score is not None else "—" for d in dimensions],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Skor: %{x}<extra></extra>",
    ))
    fig.update_layout(
        height=max(180, len(dimensions) * 38 + 60),
        margin=dict(l=10, r=40, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(range=[0, 105], gridcolor=PALETTE["border"],
                   color=PALETTE["muted"]),
        yaxis=dict(color=PALETTE["text"], autorange="reversed"),
        font=dict(color=PALETTE["text"], family="Inter"),
        showlegend=False,
    )
    return fig


def price_chart(history: list[dict[str, Any]], price_key: str = "price") -> go.Figure:
    """Fiyat geçmişi (snapshot tablosundan)."""
    if not history:
        return _empty_fig("Yeterli veri yok")
    times = [h.get("captured_at", "") for h in history]
    prices = [h.get(price_key) for h in history]
    fig = go.Figure(go.Scatter(
        x=times, y=prices, mode="lines+markers",
        line=dict(color=PALETTE["accent"], width=2),
        marker=dict(size=5, color=PALETTE["accent"]),
        hovertemplate="<b>%{x}</b><br>$%{y:.2f}<extra></extra>",
    ))
    fig.update_layout(
        height=260, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor=PALETTE["border"], color=PALETTE["muted"]),
        yaxis=dict(gridcolor=PALETTE["border"], color=PALETTE["muted"]),
        font=dict(color=PALETTE["text"], family="Inter"),
        showlegend=False,
    )
    return fig


def score_history_chart(history: list[dict[str, Any]]) -> go.Figure:
    """Snapshot tablosundaki overall_score geçmişi."""
    if not history:
        return _empty_fig("Henüz analiz geçmişi yok")
    times  = [h.get("captured_at", "") for h in history]
    scores = [h.get("overall_score")  for h in history]
    fig = go.Figure(go.Scatter(
        x=times, y=scores, mode="lines+markers", fill="tozeroy",
        line=dict(color=PALETTE["green"], width=2),
        fillcolor="rgba(46,204,113,.12)",
        marker=dict(size=6, color=PALETTE["green"]),
        hovertemplate="<b>%{x}</b><br>Skor: %{y}/100<extra></extra>",
    ))
    fig.update_layout(
        height=240, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor=PALETTE["border"], color=PALETTE["muted"]),
        yaxis=dict(range=[0, 100], gridcolor=PALETTE["border"],
                   color=PALETTE["muted"]),
        font=dict(color=PALETTE["text"], family="Inter"),
        showlegend=False,
    )
    return fig


def sentiment_donut(agg: dict[str, Any]) -> go.Figure:
    """Pozitif/Nötr/Negatif haber dağılımı — donut."""
    labels = ["Pozitif", "Nötr", "Negatif"]
    values = [agg.get("positive_count", 0), agg.get("neutral_count", 0),
              agg.get("negative_count", 0)]
    if sum(values) == 0:
        return _empty_fig("Haber yok")
    colors = [PALETTE["green"], PALETTE["muted"], PALETTE["red"]]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.6,
        marker=dict(colors=colors, line=dict(color=PALETTE["bg"], width=2)),
        textinfo="label+percent",
        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        height=240, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=PALETTE["text"], family="Inter"),
        showlegend=False,
    )
    return fig


def _empty_fig(msg: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False,
                       font=dict(color=PALETTE["muted"], size=14))
    fig.update_layout(
        height=240, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig


# ---------------------------------------------------------------- #
# HTML kartlar
# ---------------------------------------------------------------- #
def fmt_pct(v: float | None) -> str:
    if v is None: return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%"


def fmt_num(v: float | None, decimals: int = 2) -> str:
    if v is None: return "—"
    return f"{v:,.{decimals}f}"


def fmt_x(v: float | None) -> str:
    if v is None: return "—"
    return f"{v:.2f}×"


def fmt_cap(v: float | None, currency: str = "USD") -> str:
    if v is None: return "—"
    if v >= 1e6: return f"{v/1e6:.2f} T {currency}"
    if v >= 1e3: return f"{v/1e3:.2f} B {currency}"
    return f"{v:.0f} M {currency}"


def verdict_badge(label: str, color: str) -> str:
    return (f"<span class='badge' style='background:{color}22;color:{color}'>"
            f"{label}</span>")


def chg_badge(value: float | None) -> str:
    if value is None: return "<span style='color:#8a96ad'>—</span>"
    cls = "chg-up" if value >= 0 else "chg-down"
    arrow = "▲" if value >= 0 else "▼"
    return f"<span class='{cls}'>{arrow} {value:+.2f}%</span>"
