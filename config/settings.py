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
# Watchlist yükleme
# ---------------------------------------------------------------- #
def load_watchlist() -> dict[str, Any]:
    """watchlist.json dosyasını oku."""
    with open(WATCHLIST_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_watchlist(data: dict[str, Any]) -> None:
    """watchlist.json dosyasına yaz (UI'dan değişiklik gelirse)."""
    with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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
