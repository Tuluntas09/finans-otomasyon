"""
Hisse & Emtia Analiz Otomasyonu — Streamlit ana giriş.

Çalıştırma:
    streamlit run streamlit_app.py
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from config import settings
from config.settings import (
    FINNHUB_API_KEY, all_symbols, load_watchlist, save_watchlist,
)
from core import database as db
from core.finnhub_client import InvalidApiKey, NoApiKey
from ui import dashboard, news_page, portfolio, stock_detail
from ui.components import PALETTE, icon, inject_css, page_head, panel


# ---------------------------------------------------------------- #
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


# ---------------------------------------------------------------- #
# Sidebar
# ---------------------------------------------------------------- #
NAV_ITEMS = [
    ("overview", "Genel Bakış",       "overview"),
    ("detail",   "Sembol Detayı",     "detail"),
    ("news",     "Haberler",          "news"),
    ("rec",      "Yatırım Önerisi",   "rec"),
    ("settings", "Ayarlar",           "settings"),
]


def _sidebar(symbols: list[str]) -> tuple[str, str | None]:
    with st.sidebar:
        # Brand
        st.markdown(f"""
        <div class='brand'>
          <div class='brand-mark'>{icon('brand', w=20)}</div>
          <div>
            <div class='brand-name'>Finans Otomasyonu</div>
            <div class='brand-sub'>hisse · emtia analiz</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div class='nav-label'>Menü</div>",
                    unsafe_allow_html=True)

        # Nav — radio'yu CSS ile nav-item gibi göstereceğiz
        labels = [f"{lbl}" for _, lbl, _ in NAV_ITEMS]
        # Önceki seçimi koru
        page_idx_default = st.session_state.get("nav_idx", 0)
        chosen_label = st.radio(
            "Menü",
            labels,
            index=page_idx_default,
            label_visibility="collapsed",
            key="nav_radio",
        )
        page_idx = labels.index(chosen_label)
        st.session_state["nav_idx"] = page_idx
        page_id = NAV_ITEMS[page_idx][0]

        # Sembol seçici — sembol detayı sayfasında olunca üstte göster
        selected_symbol = st.session_state.get("detail_symbol", symbols[0] if symbols else None)
        if page_id == "detail":
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            selected_symbol = st.selectbox(
                "Sembol",
                symbols,
                index=symbols.index(selected_symbol) if selected_symbol in symbols else 0,
                label_visibility="collapsed",
            )
            st.session_state["detail_symbol"] = selected_symbol

        # ── Tweaks ────────────────────────────────────────────
        st.markdown(
            "<div style='border-top:1px solid var(--line); margin:14px 0 10px;'></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='nav-label' style='margin-bottom:8px;'>Vurgu Rengi</div>",
            unsafe_allow_html=True,
        )
        ACCENT_OPTIONS = {
            "Mavi":  "#3b9eff",
            "Yeşil": "#35d07f",
            "Amber": "#e8a13a",
            "Mor":   "#9a7bf0",
        }
        current_accent = st.session_state.get("accent", "#3b9eff")
        accent_cols = st.columns(4)
        for i, (label, hex_val) in enumerate(ACCENT_OPTIONS.items()):
            with accent_cols[i]:
                is_sel = current_accent == hex_val
                border = "2px solid white" if is_sel else "2px solid transparent"
                if st.button(
                    "✓" if is_sel else " ",
                    key=f"accent_{hex_val}",
                    help=label,
                ):
                    st.session_state["accent"] = hex_val
                    st.rerun()
                # Renk swatch
                st.markdown(
                    f"<div style='width:100%; height:6px; border-radius:3px; "
                    f"background:{hex_val}; margin-top:-6px;'></div>",
                    unsafe_allow_html=True,
                )

        # Yoğunluk
        st.markdown(
            "<div class='nav-label' style='margin:12px 0 6px;'>Yoğunluk</div>",
            unsafe_allow_html=True,
        )
        density = st.select_slider(
            "Yoğunluk",
            options=["Kompakt", "Normal", "Geniş"],
            value=st.session_state.get("density", "Normal"),
            label_visibility="collapsed",
            key="density_slider",
        )
        st.session_state["density"] = density

        # Otomatik yenileme
        st.markdown(
            "<div style='border-top:1px solid var(--line); margin:14px 0 10px;'></div>",
            unsafe_allow_html=True,
        )
        auto_refresh = st.checkbox(
            "Otomatik Yenile (5 dk)",
            value=st.session_state.get("auto_refresh", False),
            key="auto_refresh_cb",
            help="Her 5 dakikada sayfayı otomatik günceller",
        )
        st.session_state["auto_refresh"] = auto_refresh

        # Alt sabit blok: run butonu + cron durumu
        st.markdown("<div style='flex:1; min-height:12vh'></div>",
                    unsafe_allow_html=True)

        if st.button(f"🔄  Şimdi Çalıştır", use_container_width=True,
                     key="run_btn"):
            with st.spinner("Veri çekiliyor… (~30-60 sn)"):
                from jobs.daily_snapshot import run_snapshot
                try:
                    summary = run_snapshot()
                    st.success(f"✓ {summary['ok']}/{summary['total']} sembol "
                               f"· {summary['news_added']} yeni haber")
                except (NoApiKey, InvalidApiKey) as exc:
                    st.error(f"API: {exc}")
                except Exception as exc:
                    st.error(f"Hata: {exc}")
                st.rerun()

        # Cron durumu
        last = db.last_run("daily_snapshot")
        if last:
            status = (last.get("status", "?") or "?").lower()
            dot_cls = {"ok": "ok", "partial": "warn",
                       "failed": "err"}.get(status, "warn")
            status_text = {"ok": "başarılı", "partial": "kısmen",
                           "failed": "başarısız"}.get(status, "?")
            finished = (last.get("finished_at") or "")[:16].replace("T", " ")
            text = f"Son çalıştırma {finished} · {status_text}"
        else:
            dot_cls, text = "warn", "Henüz çalıştırma yok"
        st.markdown(
            f"<div class='cron-status'>"
            f"<span class='dot {dot_cls}'></span><span>{text}</span></div>",
            unsafe_allow_html=True,
        )

        return page_id, selected_symbol


# ---------------------------------------------------------------- #
# Ayarlar sayfası
# ---------------------------------------------------------------- #
def _settings_page() -> None:
    st.markdown(
        "<div class='page'>" + page_head(
            "Ayarlar",
            sub="API, watchlist ve otomasyon yapılandırması",
        ),
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns([1, 1])

    with col_a:
        has_key = bool(_resolve_api_key())
        items = [
            ("Finnhub API",       has_key, "fiyat · temel · haber"),
            ("VADER Sentiment",   True,    "yerel model"),
            ("Snapshot Deposu",   True,    "SQLite · 90 gün"),
        ]
        rows = ""
        for k, ok, note in items:
            sw_class = "pos" if ok else "neg"
            sw_text = "Yüklü" if ok else "Eksik"
            rows += (
                f"<div class='row between' style='padding:11px 13px; "
                f"background:var(--bg-inset); border:1px solid var(--line); "
                f"border-radius:var(--r); margin-bottom:10px;'>"
                f"<div>"
                f"<div class='hi' style='font-size:13px; font-weight:500;'>{k}</div>"
                f"<div class='faint tiny mono' style='margin-top:2px;'>{note}</div>"
                f"</div>"
                f"<span class='sent-chip {sw_class}'>"
                f"<span class='dot {sw_class if sw_class == 'pos' else 'err'}' "
                f"style='width:6px;height:6px;'></span> {sw_text}</span>"
                f"</div>"
            )
        st.markdown(
            panel("API Anahtar Durumu", rows, ico="key"),
            unsafe_allow_html=True,
        )

    with col_b:
        st.markdown(
            f"<div class='panel'>"
            f"<div class='panel-head'>"
            f"<div class='panel-title'><span class='ico'>{icon('list')}</span>Watchlist Düzenle</div>"
            f"<span class='panel-note'>SEMBOL — İSİM</span>"
            f"</div>"
            f"<div class='panel-body'>",
            unsafe_allow_html=True,
        )
        wl = load_watchlist()
        all_items = wl["stocks"] + wl["commodities"]
        wl_text = "\n".join(f"{s['symbol']} — {s.get('name', '')}"
                            for s in all_items)
        new_text = st.text_area(
            "Watchlist", value=wl_text, height=200,
            label_visibility="collapsed", key="wl_text",
        )
        st.markdown(
            f"<div class='row between' style='margin-top:8px;'>"
            f"<span class='faint tiny'>{len(all_items)} sembol</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button("Kaydet", key="save_wl"):
            # Mevcut emtia sembollerini sakla (type bilgisini koru)
            existing_commodities = {c["symbol"] for c in wl["commodities"]}
            stocks, commodities = [], []
            for line in new_text.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                # Format: "SEMBOL — İsim" veya "SEMBOL — İsim [ETF]"
                is_etf = "[ETF]" in line or "[etf]" in line
                line_clean = line.replace("[ETF]", "").replace("[etf]", "").strip()
                parts = line_clean.split("—", 1) if "—" in line_clean else line_clean.split("-", 1)
                sym = parts[0].strip().upper()
                name = parts[1].strip() if len(parts) > 1 else sym
                if not sym:
                    continue
                # Kural: [ETF] tag'i varsa emtia; yoksa eski listede emtia ise emtia; değilse hisse
                if is_etf or sym in existing_commodities:
                    commodities.append({"symbol": sym, "name": name})
                else:
                    stocks.append({"symbol": sym, "name": name})
            wl["stocks"] = stocks
            wl["commodities"] = commodities
            save_watchlist(wl)
            st.success(f"✓ Watchlist güncellendi — {len(stocks)} hisse, {len(commodities)} emtia ETF")
            st.rerun()
        st.markdown("</div></div>", unsafe_allow_html=True)

    # Cron çalıştırma geçmişi
    with db.conn() as c:
        rows = c.execute(
            "SELECT * FROM run_log ORDER BY started_at DESC LIMIT 20"
        ).fetchall()
    rows_html = ""
    for r in rows:
        status = (r["status"] or "warn").lower()
        # backend "ok"/"partial"/"failed" → ui "ok"/"warn"/"err"
        ui_status = {"ok": "ok", "partial": "warn",
                     "failed": "err"}.get(status, "warn")
        status_label = {"ok": "Başarılı", "partial": "Uyarı",
                        "failed": "Hata"}.get(status, status)
        started = (r["started_at"] or "")[:16].replace("T", " ")
        finished = (r["finished_at"] or "")
        # Süre — saniye cinsinden hesapla
        dur = "—"
        if r["started_at"] and r["finished_at"]:
            try:
                t0 = datetime.fromisoformat(r["started_at"])
                t1 = datetime.fromisoformat(r["finished_at"])
                dur = f"{(t1 - t0).total_seconds():.0f}s"
            except ValueError:
                pass
        chip_class = "pos" if ui_status == "ok" else ("neg" if ui_status == "err" else "neu")
        chip = (f"<span class='sent-chip {chip_class}'>"
                f"<span class='dot {ui_status}' style='width:6px;height:6px;'></span> "
                f"{status_label}</span>")
        rows_html += (
            f"<tr>"
            f"<td class='mono hi'>{started}</td>"
            f"<td>{chip}</td>"
            f"<td class='r mono'>{dur}</td>"
            f"<td class='muted'>{r['detail'] or '—'}</td>"
            f"</tr>"
        )
    table = (
        f"<div class='tbl-wrap'><table class='tbl'>"
        f"<thead><tr><th>Zaman</th><th>Durum</th>"
        f"<th class='r'>Süre</th><th>Not</th></tr></thead>"
        f"<tbody>{rows_html or '<tr><td colspan=4 class=muted>Henüz çalıştırma yok</td></tr>'}</tbody>"
        f"</table></div>"
    )
    st.markdown(
        "<div style='height:14px'></div>" +
        panel("Son Cron Çalıştırmaları", table, ico="clock",
              right="<span class='panel-note'>her gün 09:00</span>",
              pad=False),
        unsafe_allow_html=True,
    )

    # ── E-posta Bildirimleri Paneli ──────────────────────────────────
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    _email_panel()

    # ── Veritabanı Sağlığı Paneli ────────────────────────────────────
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    _db_health_panel()

    st.markdown("</div>", unsafe_allow_html=True)  # .page


def _email_panel() -> None:
    """Ayarlar sayfasında e-posta bildirim durumu ve test butonu."""
    from core.notifier import is_configured, send_test_email
    import config.settings as s

    configured = is_configured()
    recipient  = s.ALERT_EMAIL or s.SMTP_USER or "—"
    host_port  = f"{s.SMTP_HOST}:{s.SMTP_PORT}" if s.SMTP_HOST else "—"

    status_items = [
        ("SMTP Host",       bool(s.SMTP_HOST),  host_port),
        ("Kullanıcı",       bool(s.SMTP_USER),  s.SMTP_USER or "—"),
        ("Şifre",           bool(s.SMTP_PASS),  "••••••••" if s.SMTP_PASS else "—"),
        ("Alıcı E-posta",   bool(recipient != "—"), recipient),
    ]
    rows_html = ""
    for label, ok, val in status_items:
        cls  = "pos" if ok else "neg"
        dot  = "ok"  if ok else "err"
        rows_html += (
            f"<div class='row between' style='padding:9px 13px; "
            f"background:var(--bg-inset); border:1px solid var(--line); "
            f"border-radius:var(--r); margin-bottom:8px;'>"
            f"<div class='hi' style='font-size:12.5px;'>{label}</div>"
            f"<div style='display:flex; align-items:center; gap:10px;'>"
            f"<span class='mono faint tiny'>{val}</span>"
            f"<span class='sent-chip {cls}'>"
            f"<span class='dot {dot}' style='width:6px;height:6px;'></span> "
            f"{'Tanımlı' if ok else 'Eksik'}</span>"
            f"</div></div>"
        )

    how_to = (
        "<div class='disclaimer' style='margin-top:12px;'>"
        "Gmail için: Hesap → Güvenlik → Uygulama Şifreleri → 16 haneli şifre oluştur.<br>"
        "Sonra <code>.env</code>'e ekle: "
        "<code>SMTP_HOST=smtp.gmail.com</code>, "
        "<code>SMTP_USER</code>, <code>SMTP_PASS</code>, <code>ALERT_EMAIL</code>"
        "</div>"
    ) if not configured else ""

    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.markdown(
            panel("E-posta Bildirimleri", rows_html + how_to, ico="bell"),
            unsafe_allow_html=True,
        )
    with col_btn:
        st.markdown(
            f"<div class='panel' style='height:100%; display:flex; flex-direction:column; "
            f"justify-content:center; padding:16px; gap:10px;'>"
            f"<div class='panel-title' style='font-size:12px;'>"
            f"<span class='ico'>{icon('bell')}</span>Test</div>"
            f"<div class='muted tiny'>Yapılandırma doğru çalışıyor mu?</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button(
            "✉ Test Gönder",
            key="email_test_btn",
            disabled=not configured,
            use_container_width=True,
            help="Ayarlar geçerliyse hedef adrese test e-postası gönderir",
        ):
            with st.spinner("Gönderiliyor…"):
                ok, msg = send_test_email()
            if ok:
                st.success(msg)
            else:
                st.error(msg)


def _db_health_panel() -> None:
    """Ayarlar sayfasında veritabanı sağlık durumu ve manuel temizleme."""
    stats = db.db_stats()

    # ── 4 metrik sütun ───────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("DB Boyutu", f"{stats['file_size_kb']} KB")
    with m2:
        st.metric("WAL Boyutu", f"{stats['wal_size_kb']} KB",
                  help="WAL dosyası >10 MB olursa VACUUM gerekebilir")
    with m3:
        st.metric("Şema Versiyonu", f"v{stats['schema_version']}")
    with m4:
        integrity_label = "✓ Sağlıklı" if stats["integrity_ok"] else "✗ BOZUK"
        st.metric("Bütünlük", integrity_label)

    # ── Tablo satır tablosu ───────────────────────────────────────
    table_labels = {
        "snapshots": "Fiyat Anlık Görüntüleri",
        "news":      "Haberler",
        "scores":    "Boyut Skorları",
        "alerts":    "Uyarılar",
        "run_log":   "Çalıştırma Günlüğü",
    }
    table_rows_html = ""
    for tbl, label in table_labels.items():
        s = stats["tables"].get(tbl, {})
        count  = s.get("count", 0)
        latest = (s.get("latest") or "—")[:16].replace("T", " ")
        oldest = (s.get("oldest") or "—")[:10]
        table_rows_html += (
            f"<tr>"
            f"<td class='hi'>{label}</td>"
            f"<td class='r mono'>{count:,}</td>"
            f"<td class='mono faint'>{oldest}</td>"
            f"<td class='mono faint'>{latest}</td>"
            f"</tr>"
        )

    # Uyarı banner'ları
    warn_html = ""
    if not stats["integrity_ok"]:
        warn_html += ("<div class='disclaimer' style='color:var(--neg);margin-top:10px;'>"
                      "⚠ Veritabanı bütünlük kontrolü başarısız. Yedekten geri yüklemeyi düşünün.</div>")
    if stats["null_score_count"] > 0:
        warn_html += (f"<div class='disclaimer' style='margin-top:8px;'>"
                      f"{stats['null_score_count']} snapshot'ta skor hesaplanamamış.</div>")
    if stats["wal_size_kb"] > 10_240:
        warn_html += ("<div class='disclaimer' style='margin-top:8px;'>"
                      "WAL dosyası büyük (>10 MB). Manuel VACUUM çalıştırabilirsiniz.</div>")

    tbl_html = (
        f"<div class='tbl-wrap'><table class='tbl'>"
        f"<thead><tr><th>Tablo</th><th class='r'>Satır</th>"
        f"<th>İlk Kayıt</th><th>Son Kayıt</th></tr></thead>"
        f"<tbody>{table_rows_html}</tbody></table></div>"
        f"{warn_html}"
    )

    col_tbl, col_btn = st.columns([3, 1])
    with col_tbl:
        st.markdown(
            panel("Veritabanı Sağlığı", tbl_html, ico="database",
                  right=f"<span class='panel-note'>WAL · v{stats['schema_version']}</span>",
                  pad=False),
            unsafe_allow_html=True,
        )
    with col_btn:
        st.markdown(
            f"<div class='panel' style='height:100%; display:flex; flex-direction:column; "
            f"justify-content:center; padding:16px; gap:8px;'>"
            f"<div class='panel-title' style='font-size:12px;'>"
            f"<span class='ico'>{icon('trash')}</span>Veri Temizliği</div>"
            f"<div class='muted tiny' style='line-height:1.4;'>Retention politikasına göre "
            f"eski kayıtları sil</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button(
            "🗑 Temizle",
            key="purge_db_btn",
            use_container_width=True,
            help="snapshots:365g · news:90g · alerts:180g · run_log:90g",
        ):
            with st.spinner("Temizleniyor…"):
                purged = db.purge_old_data()
            total = sum(purged.values())
            if total > 0:
                st.success(f"{total} kayıt silindi")
            else:
                st.info("Silinecek eski kayıt yok")
            st.rerun()


# ---------------------------------------------------------------- #
# Main
# ---------------------------------------------------------------- #
def main() -> None:
    st.set_page_config(
        page_title="Finans Otomasyonu",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()
    db.init_db()

    # Accent rengi dinamik override (session_state'den)
    accent = st.session_state.get("accent", "#3b9eff")
    if accent != "#3b9eff":  # sadece default'tan farklıysa inject et
        st.html(f"<style>:root {{ --accent: {accent}; --accent-d: {accent}cc; }}</style>")

    # Yoğunluk ayarı — tablo padding override
    density = st.session_state.get("density", "Normal")
    density_css = {
        "Kompakt": "8px 8px",
        "Normal":  "9px 10px",
        "Geniş":   "12px 14px",
    }.get(density, "9px 10px")
    st.html(f"<style>.tbl tbody td, .tbl thead th {{ padding: {density_css} !important; }}</style>")

    key = _resolve_api_key()
    symbols = all_symbols()
    page_id, selected = _sidebar(symbols)

    if not key and page_id != "settings":
        st.markdown(
            "<div class='page'>" + page_head(
                "API anahtarı yok",
                sub="Ayarlar sayfasından ekle ya da .env'e koy",
            ) +
            f"<div class='panel'><div class='panel-body'>"
            f"<div class='row' style='gap:12px;'>"
            f"<span class='dot err'></span>"
            f"<div>"
            f"<div class='hi' style='font-weight:600;'>FINNHUB_API_KEY tanımlı değil</div>"
            f"<div class='muted tiny' style='margin-top:4px;'>"
            f"<code>.env</code> dosyasına <code>FINNHUB_API_KEY=...</code> ekle. "
            f"Ücretsiz: <a href='https://finnhub.io/register' target='_blank'>finnhub.io/register</a>"
            f"</div></div></div></div></div></div>",
            unsafe_allow_html=True,
        )
        st.stop()

    if page_id == "overview":
        dashboard.render(symbols)
    elif page_id == "detail":
        if selected:
            stock_detail.render(selected, symbols)
    elif page_id == "news":
        news_page.render(symbols)
    elif page_id == "rec":
        portfolio.render(symbols)
    elif page_id == "settings":
        _settings_page()

    # ── Otomatik yenileme ────────────────────────────────────────────
    # streamlit-autorefresh: sayfa render tamamlandıktan sonra N ms'de rerun
    # session_state korunur (window.location.reload() değil, st.rerun() eşdeğeri)
    if st.session_state.get("auto_refresh", False):
        try:
            from streamlit_autorefresh import st_autorefresh  # type: ignore[import]
            st_autorefresh(interval=300_000, key="autorefresh_tick")
        except ImportError:
            st.sidebar.caption("⚠ streamlit-autorefresh kurulu değil. "
                               "`pip install streamlit-autorefresh`")


if __name__ == "__main__":
    main()
