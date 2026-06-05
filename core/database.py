"""
SQLite veritabanı katmanı.

Tablolar:
  - snapshots  : Günlük fiyat + skor anlık görüntüleri (zaman serisi)
  - news       : Çekilen haberler + sentiment skoru
  - scores     : Boyut bazlı skorların geçmişi (analiz trendi için)
  - alerts     : Üretilen uyarılar (ör: skor 60 → 75 atladı)
  - run_log    : Cron job'ların ne zaman koştuğu

Tüm sorgular bağlam yöneticisi (with conn()) ile çalıştırılır.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from config.settings import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol        TEXT NOT NULL,
    asset_type    TEXT NOT NULL,                  -- 'stock' | 'commodity'
    captured_at   TEXT NOT NULL,                  -- ISO-8601 UTC
    price         REAL,
    change_pct    REAL,
    overall_score INTEGER,
    verdict       TEXT,
    raw_payload   TEXT,                           -- JSON snapshot (quote+metrics)
    UNIQUE(symbol, captured_at)
);
CREATE INDEX IF NOT EXISTS idx_snapshots_symbol ON snapshots(symbol);
CREATE INDEX IF NOT EXISTS idx_snapshots_date   ON snapshots(captured_at);

CREATE TABLE IF NOT EXISTS scores (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT NOT NULL,
    captured_at  TEXT NOT NULL,
    dimension    TEXT NOT NULL,                   -- valuation / profitability / ...
    score        INTEGER,
    UNIQUE(symbol, captured_at, dimension)
);
CREATE INDEX IF NOT EXISTS idx_scores_symbol ON scores(symbol);

CREATE TABLE IF NOT EXISTS news (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT NOT NULL,
    finnhub_id   INTEGER,                         -- Finnhub'ın haber id'si
    headline     TEXT,
    summary      TEXT,
    source       TEXT,
    url          TEXT,
    image_url    TEXT,
    published_at TEXT,                            -- ISO UTC
    sentiment    REAL,                            -- -1.0 .. +1.0 (compound)
    category     TEXT,                            -- earnings/ma/regulatory/...
    captured_at  TEXT NOT NULL,
    UNIQUE(symbol, finnhub_id)
);
CREATE INDEX IF NOT EXISTS idx_news_symbol   ON news(symbol);
CREATE INDEX IF NOT EXISTS idx_news_pub_date ON news(published_at);

CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    kind         TEXT NOT NULL,                   -- score_jump / verdict_change / news_spike
    severity     TEXT,                            -- info / warning / critical
    message      TEXT,
    payload      TEXT                             -- JSON ek bilgi
);
CREATE INDEX IF NOT EXISTS idx_alerts_symbol ON alerts(symbol);
CREATE INDEX IF NOT EXISTS idx_alerts_date   ON alerts(created_at);

CREATE TABLE IF NOT EXISTS run_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name    TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    status      TEXT,                              -- ok / failed / partial
    detail      TEXT
);
"""

# ---------------------------------------------------------------- #
# Schema Migration Sistemi
# ---------------------------------------------------------------- #
CURRENT_SCHEMA_VERSION = 1

# Her versiyon → uygulanacak SQL listesi.
# Kural: sadece EKLE, değiştirme/silme yapma.
# Yeni sütun örneği: "ALTER TABLE snapshots ADD COLUMN data_source TEXT DEFAULT 'finnhub'"
MIGRATIONS: dict[int, list[str]] = {
    1: [],   # Başlangıç versiyonu — mevcut tablolar zaten var (IF NOT EXISTS idempotent)
             # Boş liste: yalnızca schema_version=1 kaydı yazar.
    # 2: ["ALTER TABLE snapshots ADD COLUMN data_source TEXT DEFAULT 'finnhub'"],
    # 3: [...],
}

_SCHEMA_VERSION_DDL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL,
    description TEXT
);
"""


def _get_db_version(c: sqlite3.Connection) -> int:
    """Mevcut DB şema versiyonunu döndür. Tablo yoksa 0."""
    try:
        row = c.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
        return int(row["v"]) if row and row["v"] is not None else 0
    except sqlite3.OperationalError:
        return 0  # schema_version tablosu henüz yok


def _apply_migrations(c: sqlite3.Connection) -> None:
    """
    Eksik migration'ları sırayla uygula.
    Her migration kendi transaction'ında — başarısız olursa rollback + exception.
    """
    # schema_version tablosunu garantiye al
    c.executescript(_SCHEMA_VERSION_DDL)
    c.commit()

    current = _get_db_version(c)

    for version in sorted(MIGRATIONS.keys()):
        if version <= current:
            continue   # zaten uygulanmış

        try:
            for sql in MIGRATIONS[version]:
                c.execute(sql)
            c.execute(
                "INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (?, ?)",
                (version, _now_iso()),
            )
            c.commit()
        except Exception as exc:
            c.rollback()
            raise RuntimeError(
                f"Migration v{version} başarısız: {exc}  "
                f"(DB v{current}'de kaldı)"
            ) from exc


def init_db() -> None:
    """Veritabanını oluştur, şemayı ve migration'ları uygula. Idempotent."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    # conn() kullanmıyoruz: migration kendi transaction kontrolünü yönetmeli
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode = WAL")
    c.execute("PRAGMA foreign_keys = ON")
    try:
        c.executescript(SCHEMA)       # CREATE TABLE IF NOT EXISTS — backward compat
        _apply_migrations(c)
    finally:
        c.close()


@contextmanager
def conn() -> Iterator[sqlite3.Connection]:
    """
    Bağlam yöneticisi — WAL mode, busy timeout, auto commit + rollback + close.

    WAL (Write-Ahead Logging): reader ve writer birbirini bloklamaz.
    GitHub Actions cron job + Streamlit eş zamanlı çalıştığında 'database is locked'
    hatasını önler.
    """
    c = sqlite3.connect(DB_PATH, timeout=30)        # OS-level 30s retry
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode = WAL")           # reader/writer çakışmasını engeller
    c.execute("PRAGMA busy_timeout = 5000")          # SQLite-level 5 sn bekle
    c.execute("PRAGMA foreign_keys = ON")            # FK kısıtlamaları
    c.execute("PRAGMA wal_autocheckpoint = 1000")    # WAL şişmesini önler
    c.execute("PRAGMA synchronous = NORMAL")         # performans/güvenlik dengesi
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()    # hata durumunda yarım transaction'ı geri al
        raise
    finally:
        c.close()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- #
# Snapshot
# ---------------------------------------------------------------- #
def save_snapshot(
    symbol: str,
    asset_type: str,
    price: float | None,
    change_pct: float | None,
    overall_score: int | None,
    verdict: str | None,
    payload: dict[str, Any],
    dim_scores: dict[str, int | None] | None = None,
    captured_at: str | None = None,
) -> int:
    captured_at = captured_at or _now_iso()
    with conn() as c:
        cur = c.execute(
            """INSERT OR REPLACE INTO snapshots
                 (symbol, asset_type, captured_at, price, change_pct,
                  overall_score, verdict, raw_payload)
               VALUES (?,?,?,?,?,?,?,?)""",
            (symbol, asset_type, captured_at, price, change_pct,
             overall_score, verdict, json.dumps(payload, default=str)),
        )
        snap_id = cur.lastrowid
        if dim_scores:
            c.executemany(
                """INSERT OR REPLACE INTO scores
                     (symbol, captured_at, dimension, score)
                   VALUES (?,?,?,?)""",
                [(symbol, captured_at, dim, sc) for dim, sc in dim_scores.items()],
            )
        return snap_id


def latest_snapshot(symbol: str) -> dict[str, Any] | None:
    with conn() as c:
        row = c.execute(
            """SELECT * FROM snapshots
               WHERE symbol = ?
               ORDER BY captured_at DESC LIMIT 1""",
            (symbol,),
        ).fetchone()
        return dict(row) if row else None


def snapshot_history(symbol: str, days: int = 90) -> list[dict[str, Any]]:
    with conn() as c:
        rows = c.execute(
            """SELECT captured_at, price, change_pct, overall_score, verdict
               FROM snapshots
               WHERE symbol = ?
                 AND captured_at >= datetime('now', ?)
               ORDER BY captured_at ASC""",
            (symbol, f"-{days} days"),
        ).fetchall()
        return [dict(r) for r in rows]


def score_history(symbol: str, days: int = 90) -> list[dict[str, Any]]:
    """Boyut bazlı skor trendi."""
    with conn() as c:
        rows = c.execute(
            """SELECT captured_at, dimension, score
               FROM scores
               WHERE symbol = ?
                 AND captured_at >= datetime('now', ?)
               ORDER BY captured_at ASC""",
            (symbol, f"-{days} days"),
        ).fetchall()
        return [dict(r) for r in rows]


def latest_for_all(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """Birden çok sembol için en son snapshot — tek SQL sorgusuyla."""
    if not symbols:
        return {}
    placeholders = ",".join("?" * len(symbols))
    with conn() as c:
        rows = c.execute(
            f"""SELECT s.*
                FROM snapshots s
                INNER JOIN (
                    SELECT symbol, MAX(captured_at) AS max_at
                    FROM snapshots
                    WHERE symbol IN ({placeholders})
                    GROUP BY symbol
                ) latest ON s.symbol = latest.symbol
                         AND s.captured_at = latest.max_at""",
            symbols,
        ).fetchall()
    return {dict(r)["symbol"]: dict(r) for r in rows}


# ---------------------------------------------------------------- #
# Haberler
# ---------------------------------------------------------------- #
def save_news(symbol: str, items: list[dict[str, Any]]) -> int:
    """Haberleri yaz. (symbol, finnhub_id) tekilliği zaten DB'de var."""
    if not items:
        return 0
    captured = _now_iso()
    rows = [
        (
            symbol,
            n.get("id"),
            n.get("headline"),
            n.get("summary"),
            n.get("source"),
            n.get("url"),
            n.get("image"),
            n.get("published_at"),
            n.get("sentiment"),
            n.get("category"),
            captured,
        )
        for n in items
    ]
    with conn() as c:
        cur = c.executemany(
            """INSERT OR IGNORE INTO news
                 (symbol, finnhub_id, headline, summary, source, url,
                  image_url, published_at, sentiment, category, captured_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )
        return cur.rowcount


def recent_news(symbol: str, limit: int = 30) -> list[dict[str, Any]]:
    with conn() as c:
        rows = c.execute(
            """SELECT * FROM news
               WHERE symbol = ?
               ORDER BY published_at DESC LIMIT ?""",
            (symbol, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def avg_sentiment(symbol: str, days: int = 14) -> float | None:
    with conn() as c:
        row = c.execute(
            """SELECT AVG(sentiment) AS avg_s, COUNT(*) AS n
               FROM news
               WHERE symbol = ?
                 AND published_at >= datetime('now', ?)
                 AND sentiment IS NOT NULL""",
            (symbol, f"-{days} days"),
        ).fetchone()
        if not row or not row["n"]:
            return None
        return float(row["avg_s"])


# ---------------------------------------------------------------- #
# Uyarılar
# ---------------------------------------------------------------- #
def save_alert(
    symbol: str,
    kind: str,
    severity: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    with conn() as c:
        c.execute(
            """INSERT INTO alerts (symbol, created_at, kind, severity, message, payload)
               VALUES (?,?,?,?,?,?)""",
            (symbol, _now_iso(), kind, severity, message,
             json.dumps(payload or {}, default=str)),
        )


def recent_alerts(limit: int = 50) -> list[dict[str, Any]]:
    with conn() as c:
        rows = c.execute(
            """SELECT * FROM alerts
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------- #
# Run log
# ---------------------------------------------------------------- #
def log_run_start(job_name: str) -> int:
    with conn() as c:
        cur = c.execute(
            "INSERT INTO run_log (job_name, started_at) VALUES (?, ?)",
            (job_name, _now_iso()),
        )
        return cur.lastrowid


def log_run_end(run_id: int, status: str, detail: str = "") -> None:
    with conn() as c:
        c.execute(
            """UPDATE run_log
               SET finished_at = ?, status = ?, detail = ?
               WHERE id = ?""",
            (_now_iso(), status, detail, run_id),
        )


def last_run(job_name: str) -> dict[str, Any] | None:
    with conn() as c:
        row = c.execute(
            """SELECT * FROM run_log
               WHERE job_name = ?
               ORDER BY started_at DESC LIMIT 1""",
            (job_name,),
        ).fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------- #
# Veri Retention (Temizleme)
# ---------------------------------------------------------------- #
def purge_old_data(retention: dict[str, int] | None = None) -> dict[str, int]:
    """
    Retention politikasına göre eski verileri sil.

    Args:
        retention: {'snapshots': 365, 'news': 90, ...}
                   None verilirse config.settings.RETENTION_DAYS kullanılır.

    Returns:
        Silinen satır sayıları: {'snapshots': 12, 'news': 450, ...}
    """
    from config.settings import RETENTION_DAYS
    ret = retention or RETENTION_DAYS

    # tablo → (tarih sütunu, varsayılan gün)
    _TABLE_CFG: list[tuple[str, str, int]] = [
        ("snapshots", "captured_at",  ret.get("snapshots", 365)),
        ("scores",    "captured_at",  ret.get("scores",    365)),
        ("news",      "published_at", ret.get("news",      90)),
        ("alerts",    "created_at",   ret.get("alerts",    180)),
        ("run_log",   "started_at",   ret.get("run_log",   90)),
    ]

    deleted: dict[str, int] = {}
    with conn() as c:
        for table, date_col, days in _TABLE_CFG:
            try:
                cur = c.execute(
                    f"DELETE FROM {table} WHERE {date_col} < datetime('now', ?)",
                    (f"-{days} days",),
                )
                deleted[table] = cur.rowcount
            except sqlite3.OperationalError:
                deleted[table] = 0   # tablo henüz yoksa sessizce geç
    return deleted


# ---------------------------------------------------------------- #
# DB İstatistikleri (Health Check)
# ---------------------------------------------------------------- #
def db_stats() -> dict[str, Any]:
    """
    Veritabanı sağlık bilgilerini toplar.

    Returns:
        file_size_kb, wal_size_kb, schema_version, integrity_ok,
        null_score_count, tables: {tablo: {count, latest, oldest}}
    """
    stats: dict[str, Any] = {}

    db_path = Path(DB_PATH)
    stats["file_size_kb"] = (round(db_path.stat().st_size / 1024, 1)
                             if db_path.exists() else 0)
    wal_path = Path(str(DB_PATH) + "-wal")
    stats["wal_size_kb"]  = (round(wal_path.stat().st_size / 1024, 1)
                             if wal_path.exists() else 0)

    _table_date_cols = {
        "snapshots": "captured_at",
        "news":      "published_at",
        "scores":    "captured_at",
        "alerts":    "created_at",
        "run_log":   "started_at",
    }

    with conn() as c:
        tables: dict[str, dict[str, Any]] = {}
        for table, date_col in _table_date_cols.items():
            try:
                row = c.execute(
                    f"""SELECT COUNT(*) as cnt,
                               MAX({date_col}) as latest,
                               MIN({date_col}) as oldest
                        FROM {table}"""
                ).fetchone()
                tables[table] = {
                    "count":  row["cnt"],
                    "latest": row["latest"],
                    "oldest": row["oldest"],
                }
            except sqlite3.OperationalError:
                tables[table] = {"count": 0, "latest": None, "oldest": None}
        stats["tables"] = tables

        stats["schema_version"] = _get_db_version(c)

        result = c.execute("PRAGMA quick_check").fetchone()
        stats["integrity_ok"] = (result[0] == "ok")

        stats["null_score_count"] = c.execute(
            "SELECT COUNT(*) FROM snapshots WHERE overall_score IS NULL"
        ).fetchone()[0]

    return stats
