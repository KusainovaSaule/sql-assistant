import hashlib
import json
import aiosqlite as sqlite3
import time
from pathlib import Path
from typing import Optional, Protocol

from .models import DBConnection

type ColumnProperties = dict[str, str | bool]
type Column = dict[str, ColumnProperties]
type Schema = dict[str, Column]

DB_PATH = Path(__file__).parent.parent / "_cache" / "sql_assistant.db"
DEFAULT_TTL_SECONDS = 60 * 5

class AsyncCacheProtocol(Protocol):
    """Structural interface for cache backends."""

    async def get_schema(
        self, credentials: DBConnection, dialect: str, ttl: int = ...
    ) -> Optional[Schema]: ...

    async def set_schema(
        self, credentials: DBConnection, dialect: str, schema: Schema
    ) -> None: ...

    async def invalidate_schema(
        self, credentials: DBConnection, dialect: str
    ) -> None: ...

    async def add_recommendation(
        self, operation: str, sql: str, result: dict
    ) -> None: ...

    async def get_recommendation(self, operation: str, sql: str) -> Optional[dict]: ...
    
    async def get_all_recommendations(self, limit: int = ..., offset: int = ...) -> list[dict]: ...

    async def count_recommendations(self) -> int: ...

class SQLiteCache:
    """SQLite-backed implementation of CacheProtocol."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path

    @classmethod
    async def create(cls, db_path: Path = DB_PATH) -> "SQLiteCache":
        """Async factory — use this instead of the constructor directly."""
        instance = cls(db_path)
        await instance._init_db()
        return instance

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    async def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with self._connect() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_cache (
                    cache_key   TEXT PRIMARY KEY,
                    schema_hash TEXT NOT NULL,
                    schema_json TEXT NOT NULL,
                    cached_at   REAL NOT NULL
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS recommendation_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation   TEXT NOT NULL,
                    sql         TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at  REAL NOT NULL
                )
            """)

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_rec_lookup ON recommendation_history(sql)")
            await conn.commit()

    @staticmethod
    def _make_cache_key(credentials: DBConnection, dialect: str) -> str:
        # path = "host:port/db", user identifies the schema namespace
        # password deliberately excluded
        identity = f"{dialect}:{credentials.path}:{credentials.user}"
        return hashlib.sha256(identity.encode()).hexdigest()

    @staticmethod
    def _hash_schema(schema: Schema) -> str:
        return hashlib.sha1(json.dumps(schema, sort_keys=True).encode()).hexdigest()

    async def get_schema(self, credentials: DBConnection, dialect: str,
                   ttl: int = DEFAULT_TTL_SECONDS) -> Optional[Schema]:
        key = self._make_cache_key(credentials, dialect)
        async with self._connect() as conn:
            cursor: sqlite3.Cursor = await conn.execute(
                "SELECT schema_json, cached_at FROM schema_cache WHERE cache_key = ?",
                (key,)
            )
            row: Optional[sqlite3.Row] = await cursor.fetchone()

        if row is None:
            return None
        schema_json, cached_at = row
        if time.time() - cached_at > ttl:
            return None  # stale — caller will re-fetch and overwrite
        return json.loads(schema_json)

    async def set_schema(self, credentials: DBConnection, dialect: str, schema: Schema) -> None:
        key = self._make_cache_key(credentials, dialect)
        async with self._connect() as conn:
            await conn.execute("""
                INSERT INTO schema_cache (cache_key, schema_json, schema_hash, cached_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    schema_json = excluded.schema_json,
                    schema_hash = excluded.schema_hash,
                    cached_at   = excluded.cached_at
            """, (key, json.dumps(schema), self._hash_schema(schema), time.time()))
            await conn.commit()

    async def invalidate_schema(self, credentials: DBConnection, dialect: str) -> None:
        key = self._make_cache_key(credentials, dialect)
        async with self._connect() as conn:
            await conn.execute("DELETE FROM schema_cache WHERE cache_key = ?", (key,))

    async def add_recommendation(self, operation: str, sql: str, result: dict) -> None:
        async with self._connect() as conn:
            await conn.execute(
                "INSERT INTO recommendation_history (operation, sql, result_json, created_at) VALUES (?, ?, ?, ?)",
                (operation, sql, json.dumps(result, ensure_ascii=False), time.time())
            )
            await conn.commit()

    async def get_recommendation(self, operation: str, sql: str) -> Optional[dict]:
        async with self._connect() as conn:
            cursor = await conn.execute(
                "SELECT result_json FROM recommendation_history WHERE operation = ? AND sql = ? ORDER BY id DESC LIMIT 1",
                (operation, sql)
            )
            row = await cursor.fetchone()
        return json.loads(row[0]) if row else None

    async def get_all_recommendations(self, limit: int = 50, offset: int = 0) -> list[dict]:
        async with self._connect() as conn:
            cursor = await conn.execute(
                "SELECT operation, sql, result_json, created_at FROM recommendation_history ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            rows = await cursor.fetchall()

        return [
            {
                "operation": r[0],
                "sql": r[1],
                "result": json.loads(r[2]),
                "created_at": r[3]
            } for r in rows
        ]

    async def count_recommendations(self) -> int:
        async with self._connect() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM recommendation_history")
            row = await cursor.fetchone()
        return int(row[0]) if row else 0