"""
Gerçek tarihsel fiyat verisi — yfinance üzerinden.

Neden bu dosya var?
  Finnhub ücretsiz plan'da `stock/candle` uç noktası 403 döndürüyor.
  Bu modül yfinance ile 90 günlük OHLCV verisini çeker, bellek cache'i tutar
  ve daily_snapshot.py'deki candle fallback'i olarak kullanılır.

Kullanım:
    from core.price_history import get_close_prices, get_ohlcv

    prices = get_close_prices("AAPL", days=90)   # [float, ...]  son kapanış listesi
    df     = get_ohlcv("AAPL", days=90)          # pandas DataFrame (Date, Open, High, Low, Close, Volume)
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

log = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Basit bellek cache: sembol → (alınma_zamanı, data)
# ------------------------------------------------------------------ #
_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 3600  # 1 saat — yfinance ücretsiz, sık çekmeyelim


def _cache_get(key: str) -> Any | None:
    if key in _CACHE:
        ts, data = _CACHE[key]
        if time.time() - ts < _CACHE_TTL:
            return data
    return None


def _cache_set(key: str, data: Any) -> None:
    _CACHE[key] = (time.time(), data)


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #
def get_ohlcv(symbol: str, days: int = 90):
    """
    Sembol için son N günlük OHLCV verisini pandas DataFrame olarak döndürür.

    Sütunlar: Date (index), Open, High, Low, Close, Volume
    Hata durumunda boş DataFrame döner (sessiz hata).
    """
    import pandas as pd

    cache_key = f"{symbol}:{days}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        import yfinance as yf
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days + 5)  # hafta sonu kayıplarını telafi et
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start.strftime("%Y-%m-%d"),
                            end=end.strftime("%Y-%m-%d"),
                            interval="1d",
                            auto_adjust=True,
                            actions=False)
        if df.empty:
            log.warning("yfinance: %s için veri yok", symbol)
            result = pd.DataFrame()
        else:
            # Son N günü al (fazladan çektik)
            df = df.tail(days)
            result = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        log.warning("yfinance %s OHLCV hatası: %s", symbol, e)
        import pandas as pd
        return pd.DataFrame()


def get_close_prices(symbol: str, days: int = 90) -> list[float]:
    """
    Sembol için son N günlük kapanış fiyatlarını liste olarak döndürür.
    Kronolojik sırada (eskiden yeniye). Veri yoksa boş liste.
    """
    df = get_ohlcv(symbol, days=days)
    if df.empty or "Close" not in df.columns:
        return []
    return [float(v) for v in df["Close"].dropna().tolist()]


def get_latest_price(symbol: str) -> float | None:
    """yfinance'dan anlık (gecikmeli) fiyat al."""
    prices = get_close_prices(symbol, days=5)
    return prices[-1] if prices else None


def build_candles_from_yfinance(symbol: str, days: int = 365) -> dict:
    """
    Finnhub candle formatına uyumlu sözlük döndürür.
    daily_snapshot.py'de doğrudan `candles` parametresi yerine kullanılabilir.

    Dönüş formatı:
      {"s": "ok", "c": [...], "h": [...], "l": [...], "o": [...],
       "v": [...], "t": [...]}
    """
    df = get_ohlcv(symbol, days=days)
    if df.empty:
        return {"s": "no_data"}

    import math

    def _clean(series) -> list[float]:
        return [float(v) if not math.isnan(v) else 0.0
                for v in series.tolist()]

    # yfinance Date index → Unix timestamp
    timestamps = [int(dt.timestamp()) if hasattr(dt, "timestamp") else 0
                  for dt in df.index.to_pydatetime()]

    return {
        "s": "ok",
        "c": _clean(df["Close"]),
        "h": _clean(df["High"]),
        "l": _clean(df["Low"]),
        "o": _clean(df["Open"]),
        "v": _clean(df["Volume"]),
        "t": timestamps,
    }


def invalidate(symbol: str | None = None) -> None:
    """Cache temizle — test veya zorla yenileme için."""
    global _CACHE
    if symbol is None:
        _CACHE = {}
    else:
        keys = [k for k in _CACHE if k.startswith(f"{symbol}:")]
        for k in keys:
            del _CACHE[k]
