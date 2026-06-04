"""
Finnhub API istemcisi.

- Otomatik retry (tenacity) — geçici 5xx ve ağ hatalarında.
- Dakika başına istek limiti — ücretsiz planın 60/dakika sınırını aşmamak için.
- Tüm endpoint'ler tek sınıfta toplandı; analiz katmanı yalnız buradan veri çeker.

Finnhub doc: https://finnhub.io/docs/api
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import (
    FINNHUB_API_KEY,
    FINNHUB_BASE_URL,
    RATE_LIMIT_PER_MINUTE,
    REQUEST_TIMEOUT,
)

log = logging.getLogger(__name__)


class FinnhubError(Exception):
    """Finnhub kaynaklı tüm hatalar için base class."""


class NoApiKey(FinnhubError):
    pass


class InvalidApiKey(FinnhubError):
    pass


class RateLimited(FinnhubError):
    pass


class NotFound(FinnhubError):
    pass


class _RateLimiter:
    """Sliding-window rate limiter — dakikada N istek."""

    def __init__(self, max_per_minute: int) -> None:
        self.max = max_per_minute
        self.calls: deque[float] = deque()
        self.lock = threading.Lock()

    def acquire(self) -> None:
        with self.lock:
            now = time.monotonic()
            # 60 saniyeden eski çağrıları at
            while self.calls and now - self.calls[0] > 60:
                self.calls.popleft()
            if len(self.calls) >= self.max:
                wait = 60 - (now - self.calls[0]) + 0.05
                if wait > 0:
                    log.info("Rate limit yaklaştı, %.1fs bekleniyor", wait)
                    time.sleep(wait)
                    # tekrar temizle
                    now = time.monotonic()
                    while self.calls and now - self.calls[0] > 60:
                        self.calls.popleft()
            self.calls.append(time.monotonic())


class FinnhubClient:
    """
    İnce ama eksiksiz Finnhub sarmalayıcısı.

    Tüm metotlar hata durumunda FinnhubError subclass fırlatır:
      - NoApiKey       : .env'de anahtar yok
      - InvalidApiKey  : Finnhub 401/403 döndü
      - RateLimited    : 429 ve retry'lar tükendi
      - NotFound       : Sembol için veri yok / boş response
      - FinnhubError   : Diğer hatalar
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or FINNHUB_API_KEY
        if not self.api_key:
            raise NoApiKey(".env içinde FINNHUB_API_KEY tanımlı değil.")
        self.session = requests.Session()
        self.session.headers.update({"X-Finnhub-Token": self.api_key})
        self.limiter = _RateLimiter(RATE_LIMIT_PER_MINUTE)

    # ------------------------------------------------------------ #
    # Düşük seviye GET
    # ------------------------------------------------------------ #
    @retry(
        retry=retry_if_exception_type((requests.exceptions.ConnectionError,
                                       requests.exceptions.Timeout)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self.limiter.acquire()
        url = f"{FINNHUB_BASE_URL}/{path.lstrip('/')}"
        try:
            r = self.session.get(url, params=params or {}, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            raise FinnhubError(f"Ağ hatası: {exc}") from exc

        if r.status_code == 401:
            raise InvalidApiKey("API anahtarı geçersiz (401).")
        if r.status_code == 403:
            raise InvalidApiKey("API anahtarı reddedildi (403) — plan/yetki sorunu.")
        if r.status_code == 429:
            raise RateLimited("Finnhub 429 — dakika limiti aşıldı.")
        if r.status_code == 404:
            raise NotFound(f"404 — {path}")
        if r.status_code >= 500:
            raise FinnhubError(f"Finnhub sunucu hatası {r.status_code}")
        if not r.ok:
            raise FinnhubError(f"HTTP {r.status_code}: {r.text[:200]}")

        try:
            data = r.json()
        except ValueError as exc:
            raise FinnhubError("JSON parse hatası") from exc

        # Finnhub bazen 200 + {"error": "..."} dönebiliyor
        if isinstance(data, dict) and data.get("error"):
            err = str(data["error"]).lower()
            if "api limit" in err or "rate limit" in err:
                raise RateLimited(data["error"])
            if "invalid api" in err or "no api" in err:
                raise InvalidApiKey(data["error"])
            raise FinnhubError(data["error"])

        return data

    # ------------------------------------------------------------ #
    # Yüksek seviye endpoint'ler
    # ------------------------------------------------------------ #
    def quote(self, symbol: str) -> dict[str, Any]:
        """Anlık fiyat: {'c','d','dp','h','l','o','pc','t'}"""
        data = self._get("quote", {"symbol": symbol})
        if not data or data.get("c") in (None, 0):
            raise NotFound(f"{symbol} için quote verisi yok")
        return data

    def profile(self, symbol: str) -> dict[str, Any]:
        """Şirket profili: isim, logo, sektör, piyasa değeri, vb."""
        data = self._get("stock/profile2", {"symbol": symbol})
        if not data:
            # ETF veya emtia olabilir — boş profil de geçerli sayılır
            return {}
        return data

    def metrics(self, symbol: str) -> dict[str, Any]:
        """Tüm temel finansal oranlar. ETF için genellikle boş döner."""
        data = self._get("stock/metric", {"symbol": symbol, "metric": "all"})
        return (data or {}).get("metric", {}) or {}

    def recommendation(self, symbol: str) -> list[dict[str, Any]]:
        """Analist tavsiyeleri (aylık)."""
        data = self._get("stock/recommendation", {"symbol": symbol})
        return data or []

    def news(self, symbol: str, days_back: int = 14) -> list[dict[str, Any]]:
        """Şirket haberleri."""
        today = datetime.now(timezone.utc).date()
        frm = today - timedelta(days=days_back)
        data = self._get("company-news", {
            "symbol": symbol,
            "from": frm.isoformat(),
            "to": today.isoformat(),
        })
        return data or []

    def market_news(self, category: str = "general") -> list[dict[str, Any]]:
        """Genel piyasa haberleri (kategori: general, forex, crypto, merger)."""
        data = self._get("news", {"category": category})
        return data or []

    def candles(
        self,
        symbol: str,
        resolution: str = "D",
        days_back: int = 365,
    ) -> dict[str, Any]:
        """
        OHLCV mum verisi.

        NOT: Finnhub ücretsiz planda /stock/candle bazı semboller için
        kapalı olabilir. Hata olursa boş dict döner, üst katman kapatabilir.
        """
        now = int(datetime.now(timezone.utc).timestamp())
        frm = now - days_back * 86400
        try:
            data = self._get("stock/candle", {
                "symbol": symbol,
                "resolution": resolution,
                "from": frm,
                "to": now,
            })
        except FinnhubError as exc:
            log.warning("Mum verisi alınamadı (%s): %s", symbol, exc)
            return {}
        if data.get("s") != "ok":
            return {}
        return data

    def search(self, query: str) -> list[dict[str, Any]]:
        """Sembol arama."""
        data = self._get("search", {"q": query})
        return (data or {}).get("result", [])

    def health_check(self) -> bool:
        """API anahtarının geçerli olup olmadığını kontrol et."""
        try:
            self.quote("AAPL")
            return True
        except (InvalidApiKey, NoApiKey):
            return False
        except FinnhubError:
            # Geçici hata — anahtar muhtemelen iyi
            return True


# Singleton — Streamlit & job'ların paylaştığı tek istemci
_client: FinnhubClient | None = None


def get_client() -> FinnhubClient:
    """Tek paylaşımlı istemci. Anahtar değişirse yeniden kur."""
    global _client
    if _client is None or _client.api_key != FINNHUB_API_KEY:
        _client = FinnhubClient()
    return _client
