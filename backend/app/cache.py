import hashlib
import json
import aiosqlite as sqlite3
import time
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from .models import DBConnection

type Column = dict[str, str]
type Schema = dict[str, Column]

DB_PATH = Path(__file__).parent / "_cache" / "sql_assistant.db"
DEFAULT_TTL_SECONDS = 1800  # 30 minutes


@runtime_checkable
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
