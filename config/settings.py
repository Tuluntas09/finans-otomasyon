"""
Uygulama ayarları, skorlama ağırlıkları ve eşikler.

Mevcut "Hisse Analiz Motoru" projesindeki config.js dosyasının
genişletilmiş Python karşılığıdır. Eşik veya ağırlık değiştirmek
istiyorsan TEK YER burası.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# ---------------------------------------------------------------- #
# Genel
# ---------------------------------------------------------------- #
FINNHUB_API_KEY: str | None = os.getenv("FINNHUB_API_KEY")
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

DB_PATH = ROOT / "data" / "finans.db"
WATCHLIST_PATH = ROOT / "config" / "watchlist.json"

TIMEZONE = os.getenv("TIMEZONE", "Europe/Istanbul")

# ---------------------------------------------------------------- #
# E-posta bildirimleri (isteğe bağlı — .env'e SMTP_ değerleri girilirse aktif)
# ---------------------------------------------------------------- #
SMTP_HOST:   str | None = os.getenv("SMTP_HOST")        # ör: smtp.gmail.com
SMTP_PORT:   int        = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER:   str | None = os.getenv("SMTP_USER")        # gönderen e-posta
SMTP_PASS:   str | None = os.getenv("SMTP_PASS")        # uygulama şifresi
ALERT_EMAIL: str | None = os.getenv("ALERT_EMAIL")      # alıcı (boşsa SMTP_USER)

# ---------------------------------------------------------------- #
# Veri temizleme (retention) politikası — gün cinsinden
# .env'den override edilebilir: RETENTION_SNAPSHOTS_DAYS=730 vb.
# ---------------------------------------------------------------- #
RETENTION_DAYS: dict[str, int] = {
    "snapshots": int(os.getenv("RETENTION_SNAPSHOTS_DAYS", "365")),  # 1 yıl trend
    "scores":    int(os.getenv("RETENTION_SCORES_DAYS",    "365")),  # snapshot ile senkron
    "news":      int(os.getenv("RETENTION_NEWS_DAYS",      "90")),   # 90g sonra analitik değeri kalmaz
    "alerts":    int(os.getenv("RETENTION_ALERTS_DAYS",    "180")),  # 6 aylık audit trail
    "run_log":   int(os.getenv("RETENTION_RUNLOG_DAYS",    "90")),   # Ayarlar'da son 20 gösteriliyor
}

# Finnhub ücretsiz plan: 60 istek/dakika.
# Güvenlik payı bırakıyoruz: 50 istek/dakika gibi davranıyoruz.
RATE_LIMIT_PER_MINUTE = 50
REQUEST_TIMEOUT = 15  # saniye

# ---------------------------------------------------------------- #
# Skorlama ağırlıkları (toplam = 1.0)
# ---------------------------------------------------------------- #
# Hisse (stock) — 6 boyut
STOCK_WEIGHTS: dict[str, float] = {
    "valuation":    0.20,   # F/K, PD/DD, P/S
    "profitability": 0.20,  # ROE, net marj, brüt marj
    "growth":       0.20,   # Gelir & EPS büyümesi
    "health":       0.15,   # Cari oran, borç/özkaynak
    "technical":    0.15,   # 52H konum, 3 ay getiri, beta
    "analyst":      0.10,   # Konsensüs + haber sentiment
}

# Emtia ETF'leri (GLD, SLV, USO, ...) — temel veriler yok, farklı ağırlıklar
COMMODITY_WEIGHTS: dict[str, float] = {
    "technical":  0.45,  # Trend, momentum, 52H konum
    "news":       0.30,  # Sektör/emtia haberi sentiment
    "volatility": 0.15,  # Düşük vol → daha güvenilir sinyal
    "trend":      0.10,  # Uzun vadeli trend yönü
}

# ---------------------------------------------------------------- #
# Boyut bazlı eşikler — yukarı (up) veya aşağı (down) yön
# ---------------------------------------------------------------- #
# Format: { ad: (yön, [eşik1, eşik2, eşik3, eşik4]) }
#   up   → değer yüksekse iyi (ROE gibi)
#   down → değer düşükse iyi (F/K gibi)
# Skor → 92 / 74 / 55 / 38 / 18 (en iyi → en kötü)
THRESHOLDS: dict[str, tuple[str, list[float]]] = {
    "pe":            ("down", [10, 18, 25, 40]),
    "pb":            ("down", [1.5, 3.0, 5.0, 8.0]),
    "ps":            ("down", [1.5, 3.0, 6.0, 10.0]),
    "roe":           ("up",   [25, 18, 12, 6]),
    "roa":           ("up",   [12, 8, 5, 2]),
    "net_margin":    ("up",   [20, 12, 7, 3]),
    "gross_margin":  ("up",   [60, 40, 25, 15]),
    "rev_growth":    ("up",   [20, 12, 6, 0]),
    "eps_growth":    ("up",   [25, 15, 7, 0]),
    "debt_equity":   ("down", [0.3, 0.7, 1.2, 2.0]),
    "current_ratio": ("up",   [2.0, 1.5, 1.0, 0.7]),
    "beta":          ("down", [0.8, 1.1, 1.4, 1.8]),  # düşük beta → daha az risk
}

# ---------------------------------------------------------------- #
# Karar bantları (genel skor → tavsiye)
# ---------------------------------------------------------------- #
VERDICT_BANDS: list[tuple[int, str, str]] = [
    (75, "GÜÇLÜ AL", "#1f9d57"),
    (60, "AL",       "#2ecc71"),
    (45, "TUT",      "#f5b942"),
    (32, "SAT",      "#ff8a5c"),
    (0,  "GÜÇLÜ SAT","#ff5c6c"),
]

# ---------------------------------------------------------------- #
# Haber sentiment
# ---------------------------------------------------------------- #
NEWS_DAYS_BACK = 14            # son N gün haberini çek
NEWS_MAX_PER_SYMBOL = 30       # her sembol için tutulacak max haber sayısı
SENTIMENT_BANDS = [
    (0.30,  "Çok Pozitif", "#1f9d57"),
    (0.05,  "Pozitif",     "#2ecc71"),
    (-0.05, "Nötr",        "#8a96ad"),
    (-0.30, "Negatif",     "#ff8a5c"),
    (-1.01, "Çok Negatif", "#ff5c6c"),
]

# Haber kategorileri — sıra ÖNEMLİ: ilk eşleşen kazanır.
# Spesifik/önemli sinyalleri (regülasyon, M&A, bilanço) jenerik kelimelerden (launch) önce koy.
NEWS_CATEGORIES: dict[str, list[str]] = {
    "regulatory": ["sec ", "lawsuit", "investigation", "regulator", "fine ", "antitrust", "settlement", "probe"],
    "ma":         ["acquire", "acquisition", "merger", "buyout", "takeover"],
    "earnings":   ["earnings", "revenue", "eps", "guidance", "quarterly", "results", "profit"],
    "analyst":    ["upgrade", "downgrade", "price target", "rating", "analyst"],
    "leadership": ["ceo", "cfo", "resign", "appoint", "executive", "step down"],
    "macro":      ["fed ", "interest rate", "inflation", "recession", "gdp", "tariff", "fomc"],
    "tech":       ["ai ", "chip", "cloud", "data center", "model", "semiconductor"],
    "product":    ["launch", "unveil", "release", "new product"],
}

# ---------------------------------------------------------------- #
# Watchlist yükleme — module-level cache (her render'da dosya açılmıyor)
# ---------------------------------------------------------------- #
_wl_cache: dict[str, Any] | None = None
_wl_mtime: float = 0.0


def load_watchlist() -> dict[str, Any]:
    """watchlist.json dosyasını oku. Dosya değişmemişse cache'den döner."""
    global _wl_cache, _wl_mtime
    import os
    try:
        mtime = os.path.getmtime(WATCHLIST_PATH)
    except OSError:
        mtime = 0.0
    if _wl_cache is None or mtime != _wl_mtime:
        with open(WATCHLIST_PATH, encoding="utf-8") as f:
            _wl_cache = json.load(f)
        _wl_mtime = mtime
    return _wl_cache


def save_watchlist(data: dict[str, Any]) -> None:
    """watchlist.json dosyasına yaz ve cache'i temizle."""
    global _wl_cache, _wl_mtime
    with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    _wl_cache = None   # invalidate — bir sonraki load_watchlist yeniden okur
    _wl_mtime = 0.0


def all_symbols() -> list[str]:
    """Tüm sembolleri tek listede döndür."""
    w = load_watchlist()
    return [s["symbol"] for s in w["stocks"]] + [s["symbol"] for s in w["commodities"]]


def asset_type(symbol: str) -> str:
    """Sembol stok mu emtia mı?"""
    w = load_watchlist()
    if any(s["symbol"] == symbol for s in w["commodities"]):
        return "commodity"
    return "stock"


def display_name(symbol: str) -> str:
    """UI'da gösterilecek isim."""
    w = load_watchlist()
    for s in w["stocks"] + w["commodities"]:
        if s["symbol"] == symbol:
            return s.get("name", symbol)
    return symbol
