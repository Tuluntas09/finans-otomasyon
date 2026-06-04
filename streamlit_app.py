"""
Hisse & Emtia Analiz Otomasyonu — Streamlit ana giriş.

Çalıştırma:
    streamlit run streamlit_app.py
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import streamlit as st

# .env'i Streamlit Cloud + lokal her iki ortamda yükle
from config import settings
from config.settings import (
    FINNHUB_API_KEY, all_symbols, load_watchlist, save_watchlist,
)
from core import database as db
from core.finnhub_client import NoApiKey, InvalidApiKey
from ui import dashboard, news_page, portfolio, stock_detail
from ui.components import PALETTE, inject_css


# Streamlit Cloud'daki secrets.toml'dan da anahtar al
def _resolve_api_key() -> str | None:
    if FINNHUB_API_KEY:
        return FINNHUB_API_KEY
    try:
        key = st.secrets.get("FINNHUB_API_KEY")
        if key:
            os.environ["FINNHUB_API_KEY"] = key
            settings.FINNHUB_API_KEY = key  # type: ignore[attr-defined]
            return key
    except Exception:
        pass
    return None


def _sidebar(symbols: list[str]) -> tuple[str, str | None]:
    """Sidebar — sayfa seçimi + sembol seçimi + araçlar."""
    with st.sidebar:
        st.markdown(
            f"<div style='display:flex; align-items:center; gap:10px; margin-bottom:18px;'>"
            f"<div style='width:36px; height:36px; border-radius:10px; "
            f"background:linear-gradient(135deg,#4f8cff,#8a5cff); "
            f"display:grid; place-items:center; font-weight:800;'>📊</div>"
            f"<div><div style='font-weight:800;'>Finans Otomasyonu</div>"
            f"<div style='font-size:11px; color:{PALETTE['muted']};'>"
            f"Hisse + Emtia · Günlük takip</div></div></div>",
            unsafe_allow_html=True,
        )

        page = st.radio(
            "Sayfa",
            ["📊 Genel Bakış", "🔍 Sembol Detayı", "📰 Haberler",
             "💼 Yatırım Önerisi", "⚙️ Ayarlar"],
            label_visibility="collapsed",
        )

        selected_symbol = None
        if page == "🔍 Sembol Detayı":
            selected_symbol = st.selectbox("Sembol seç", symbols)

        st.markdown("---")
        st.markdown("**🔄 Veri Topla**")
        st.caption("Tüm watchlist için yeni snapshot al.")
        if st.button("Şimdi Çalıştır", use_container_width=True):
            with st.spinner("Veri çekiliyor… (12 sembol, ~30 sn)"):
                from jobs.daily_snapshot import run_snapshot
                try:
                    summary = run_snapshot()
                    st.success(
                        f"Tamamlandı — {summary['ok']}/{summary['total']} sembol başarılı, "
                        f"{summary['news_added']} yeni haber.")
                except (NoApiKey, InvalidApiKey) as exc:
                    st.error(f"API hatası: {exc}")
                except Exception as exc:
                    st.error(f"Hata: {exc}")
                st.rerun()

        st.markdown("---")
        last = db.last_run("daily_snapshot")
        if last:
            st.caption(f"Son veri toplama: {last.get('finished_at', '—')[:16]}")
            st.caption(f"Durum: **{last.get('status', '?')}**")
        else:
            st.caption("Henüz veri toplanmadı.")

        return page, selected_symbol


def _settings_page() -> None:
    st.markdown("## ⚙️ Ayarlar")

    # ---- API anahtarı ----
    st.markdown("### 🔑 Finnhub API Anahtarı")
    has_key = bool(_resolve_api_key())
    if has_key:
        st.success("API anahtarı yüklü. .env dosyasından okunuyor.")
    else:
        st.error(
            "API anahtarı bulunamadı. `.env` dosyasına şu satırı ekle:\n\n"
            "`FINNHUB_API_KEY=senin_anahtarın`\n\n"
            "Ya da Streamlit Cloud kullanıyorsan Secrets bölümüne ekle."
        )

    # ---- Watchlist düzenleme ----
    st.markdown("### 📋 Watchlist Yönetimi")
    wl = load_watchlist()

    st.markdown("#### Hisseler")
    stock_text = "\n".join(f"{s['symbol']} — {s.get('name', '')}"
                            for s in wl["stocks"])
    new_stocks = st.text_area(
        "Her satıra `SEMBOL — İSİM` (örn: `AAPL — Apple Inc.`)",
        value=stock_text, height=200,
    )

    st.markdown("#### Emtia ETF'leri")
    com_text = "\n".join(f"{s['symbol']} — {s.get('name', '')}"
                         for s in wl["commodities"])
    new_com = st.text_area(
        "Aynı format — emtia ETF'leri için",
        value=com_text, height=140,
    )

    if st.button("Kaydet", type="primary"):
        def parse(text: str) -> list[dict]:
            out = []
            for line in text.strip().splitlines():
                if not line.strip():
                    continue
                parts = line.split("—", 1) if "—" in line else line.split("-", 1)
                sym = parts[0].strip().upper()
                name = parts[1].strip() if len(parts) > 1 else sym
                if sym:
                    out.append({"symbol": sym, "name": name})
            return out

        wl["stocks"] = parse(new_stocks)
        wl["commodities"] = parse(new_com)
        save_watchlist(wl)
        st.success("Watchlist güncellendi.")
        st.rerun()

    # ---- Job geçmişi ----
    st.markdown("### 📜 Son Çalıştırmalar")
    with db.conn() as c:
        rows = c.execute(
            "SELECT * FROM run_log ORDER BY started_at DESC LIMIT 20"
        ).fetchall()
    if rows:
        import pandas as pd
        df = pd.DataFrame([dict(r) for r in rows])
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.caption("Henüz çalıştırma kaydı yok.")


def main() -> None:
    st.set_page_config(
        page_title="Finans Otomasyonu — Hisse & Emtia",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()
    db.init_db()

    # API anahtarı olmadan veri sayfalarına gitmek anlamsız → uyarı göster
    key = _resolve_api_key()

    symbols = all_symbols()
    page, selected = _sidebar(symbols)

    if not key and page != "⚙️ Ayarlar":
        st.error(
            "🔑 Finnhub API anahtarı yok. Sol menüden **Ayarlar**'a git, "
            "ya da `.env` dosyasına `FINNHUB_API_KEY=...` ekle.\n\n"
            "Ücretsiz anahtar: https://finnhub.io/register"
        )
        st.stop()

    if page == "📊 Genel Bakış":
        dashboard.render(symbols)
    elif page == "🔍 Sembol Detayı":
        if selected:
            stock_detail.render(selected)
    elif page == "📰 Haberler":
        news_page.render(symbols)
    elif page == "💼 Yatırım Önerisi":
        portfolio.render(symbols)
    elif page == "⚙️ Ayarlar":
        _settings_page()

    # Footer
    st.markdown(
        f"<div style='text-align:center; color:{PALETTE['muted']}; "
        f"font-size:12px; margin-top:30px;'>"
        f"Veriler: <a href='https://finnhub.io' target='_blank'>Finnhub.io</a> · "
        f"Bu uygulama eğitim amaçlıdır, yatırım tavsiyesi değildir.</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
