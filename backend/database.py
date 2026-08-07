"""SQLite 数据库操作层"""
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from config import DB_PATH

_lock = threading.Lock()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """初始化所有表结构"""
    with get_conn() as conn:
        c = conn.cursor()
        # 股票清单
        c.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                market TEXT NOT NULL,           -- sh / sz / bj
                secid TEXT NOT NULL,            -- 东方财富 secid (0/1.code)
                added_at TEXT NOT NULL
            )
        """)
        # 系统设置
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        # 新闻缓存
        c.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                url TEXT,
                keywords TEXT,                 -- JSON 数组 (纯文字)
                keywords_tagged TEXT,          -- JSON 数组 (带type: industry/positive/negative/general)
                industries TEXT,               -- JSON 数组 (行业标签)
                sentiment_label TEXT,           -- positive/negative/neutral
                sentiment_text TEXT,            -- 利好/利空/中性
                published_at TEXT,
                crawled_at TEXT NOT NULL,
                UNIQUE(source, title, published_at)
            )
        """)
        # 为已有表添加新字段（迁移）
        try:
            c.execute("ALTER TABLE news ADD COLUMN keywords_tagged TEXT DEFAULT '[]'")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE news ADD COLUMN industries TEXT DEFAULT '[]'")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE news ADD COLUMN sentiment_label TEXT DEFAULT 'neutral'")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE news ADD COLUMN sentiment_text TEXT DEFAULT '中性'")
        except Exception:
            pass
        # 情绪快照
        c.execute("""
            CREATE TABLE IF NOT EXISTS sentiment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                source TEXT NOT NULL,
                positive REAL NOT NULL,
                neutral REAL NOT NULL,
                negative REAL NOT NULL,
                score REAL NOT NULL,           -- -100 ~ 100
                sample_count INTEGER NOT NULL,
                positive_texts INTEGER DEFAULT 0,
                neutral_texts INTEGER DEFAULT 0,
                negative_texts INTEGER DEFAULT 0,
                level TEXT,                     -- 情绪等级
                interpretation TEXT,            -- 专业解读
                advice TEXT,                    -- 操作建议
                formula TEXT,                   -- 计算公式说明
                keywords TEXT,                 -- JSON
                created_at TEXT NOT NULL
            )
        """)
        # 情绪表迁移字段
        for col in ["positive_texts", "neutral_texts", "negative_texts",
                    "level", "interpretation", "advice", "formula"]:
            try:
                c.execute(f"ALTER TABLE sentiment ADD COLUMN {col} TEXT DEFAULT ''")
            except Exception:
                pass
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_news_stock ON news(stock_code, crawled_at)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_sentiment_stock ON sentiment(stock_code, created_at)"
        )
        # 默认设置
        from config import DEFAULT_REFRESH_INTERVAL, DEFAULT_TOP_N
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
                  ("refresh_interval", str(DEFAULT_REFRESH_INTERVAL)))
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
                  ("top_n", str(DEFAULT_TOP_N)))


# ---------------- 股票管理 ----------------

def list_stocks() -> list[dict]:
    with _lock, get_conn() as conn:
        rows = conn.execute(
            "SELECT code,name,market,secid,added_at FROM stocks ORDER BY added_at"
        ).fetchall()
        return [dict(r) for r in rows]


def get_stock(code: str) -> Optional[dict]:
    with _lock, get_conn() as conn:
        row = conn.execute(
            "SELECT code,name,market,secid,added_at FROM stocks WHERE code=?",
            (code,),
        ).fetchone()
        return dict(row) if row else None


def add_stock(code: str, name: str, market: str, secid: str) -> dict:
    with _lock, get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO stocks(code,name,market,secid,added_at) VALUES(?,?,?,?,?)",
            (code, name, market, secid, datetime.now().isoformat()),
        )
    return {"code": code, "name": name, "market": market, "secid": secid}


def remove_stock(code: str) -> bool:
    with _lock, get_conn() as conn:
        cur = conn.execute("DELETE FROM stocks WHERE code=?", (code,))
        # 同步清理缓存
        conn.execute("DELETE FROM news WHERE stock_code=?", (code,))
        conn.execute("DELETE FROM sentiment WHERE stock_code=?", (code,))
        return cur.rowcount > 0


# ---------------- 设置 ----------------

def get_setting(key: str, default: str = "") -> str:
    with _lock, get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with _lock, get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value)
        )


# ---------------- 新闻缓存 ----------------

def save_news(items: list[dict]):
    if not items:
        return
    with _lock, get_conn() as conn:
        for it in items:
            conn.execute(
                """INSERT OR IGNORE INTO news
                   (stock_code,source,title,summary,url,keywords,keywords_tagged,industries,sentiment_label,sentiment_text,published_at,crawled_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    it["stock_code"],
                    it["source"],
                    it["title"],
                    it.get("summary", ""),
                    it.get("url", ""),
                    it.get("keywords", "[]"),
                    it.get("keywords_tagged", "[]"),
                    it.get("industries", "[]"),
                    it.get("sentiment_label", "neutral"),
                    it.get("sentiment_text", "中性"),
                    it.get("published_at", ""),
                    it.get("crawled_at", datetime.now().isoformat()),
                ),
            )


def get_news(stock_code: str, limit: int = 20) -> list[dict]:
    with _lock, get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM news WHERE stock_code=? 
               ORDER BY crawled_at DESC LIMIT ?""",
            (stock_code, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def clear_news(stock_code: Optional[str] = None):
    with _lock, get_conn() as conn:
        if stock_code:
            conn.execute("DELETE FROM news WHERE stock_code=?", (stock_code,))
        else:
            conn.execute("DELETE FROM news")


# ---------------- 情绪缓存 ----------------

def save_sentiment(item: dict):
    with _lock, get_conn() as conn:
        conn.execute(
            """INSERT INTO sentiment
               (stock_code,source,positive,neutral,negative,score,
                sample_count,positive_texts,neutral_texts,negative_texts,
                level,interpretation,advice,formula,keywords,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item["stock_code"],
                item["source"],
                item["positive"],
                item["neutral"],
                item["negative"],
                item["score"],
                item["sample_count"],
                item.get("positive_texts", 0),
                item.get("neutral_texts", 0),
                item.get("negative_texts", 0),
                item.get("level", ""),
                item.get("interpretation", ""),
                item.get("advice", ""),
                item.get("formula", ""),
                item.get("keywords", "[]"),
                item.get("created_at", datetime.now().isoformat()),
            ),
        )


def get_latest_sentiment(stock_code: str) -> Optional[dict]:
    with _lock, get_conn() as conn:
        row = conn.execute(
            """SELECT * FROM sentiment WHERE stock_code=?
               ORDER BY created_at DESC LIMIT 1""",
            (stock_code,),
        ).fetchone()
        return dict(row) if row else None


def get_sentiment_history(stock_code: str, limit: int = 30) -> list[dict]:
    with _lock, get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM sentiment WHERE stock_code=?
               ORDER BY created_at DESC LIMIT ?""",
            (stock_code, limit),
        ).fetchall()
        return [dict(r) for r in rows]
