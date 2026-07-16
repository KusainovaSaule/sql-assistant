import contextlib
from typing import Any, AsyncGenerator

import asyncpg
import mysql.connector.aio as mysql

from .models import DBConnection


class SchemaExtractionError(Exception):
    """Base error for anything that goes wrong extracting a DB schema."""

class UnsupportedDialectError(SchemaExtractionError): pass
class DBConnectionError(SchemaExtractionError): pass
class InvalidDBCredentialsError(SchemaExtractionError): pass

class _DBWrapper:
    """Wrapper for DB operations to be dialect agnostic"""

    def __init__(self, connection: Any, dialect: str) -> None:
        self.connection = connection
        self.dialect = dialect

    async def fetch_schema_columns(self) -> list[tuple[str, str, str]]:
        if self.dialect == 'postgres':
            query = """
                SELECT table_name, column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public';
            """
            records = await self.connection.fetch(query)
            return [(r['table_name'], r['column_name'], r['data_type']) for r in records]
            
        elif self.dialect == 'mysql':
            query = """
                SELECT table_name, column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = DATABASE();
            """
            cur = await self.connection.cursor()
            try:
                await cur.execute(query)
                records = await cur.fetchall()
                return [(r[0], r[1], r[2]) for r in records]
            finally:
                await cur.close()
        return []

    async def fetch_primary_keys(self) -> set[tuple[str, str]]:
        """Returns set of (table_name, column_name) that are part of a primary key."""
        if self.dialect == 'postgres':
            query = """
                SELECT tc.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = 'public';
            """
            records = await self.connection.fetch(query)
            return {(r['table_name'], r['column_name']) for r in records}

        elif self.dialect == 'mysql':
            query = """
                SELECT table_name, column_name
                FROM information_schema.key_column_usage
                WHERE constraint_name = 'PRIMARY'
                  AND table_schema = DATABASE();
            """
            cur = await self.connection.cursor()
            try:
                await cur.execute(query)
                records = await cur.fetchall()
                return {(r[0], r[1]) for r in records}
            finally:
                await cur.close()
        return set()

    async def fetch_indexed_columns(self) -> set[tuple[str, str]]:
        """Returns set of (table_name, column_name) that are covered by any index."""
        if self.dialect == 'postgres':
            query = """
                SELECT t.relname AS table_name, a.attname AS column_name
                FROM pg_index ix
                JOIN pg_class t ON t.oid = ix.indrelid
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE n.nspname = 'public' AND t.relkind = 'r';
            """
            records = await self.connection.fetch(query)
            return {(r['table_name'], r['column_name']) for r in records}

        elif self.dialect == 'mysql':
            query = """
                SELECT table_name, column_name
                FROM information_schema.statistics
                WHERE table_schema = DATABASE();
            """
            cur = await self.connection.cursor()
            try:
                await cur.execute(query)
                records = await cur.fetchall()
                return {(r[0], r[1]) for r in records}
            finally:
                await cur.close()
        return set()

    async def close(self) -> None:
        await self.connection.close()

def _parse_credentials(credentials: DBConnection, dialect: str) -> tuple[str, str, str, int]:
    parts: list[str] = credentials.path.split('/')
    host_port = parts[0]
    db = parts[1] if len(parts) > 1 else ''
    
    if ':' in host_port:
        host, port_str = host_port.split(':')
        try:
            port = int(port_str)
        except ValueError:
            raise InvalidDBCredentialsError(f"Invalid port: {port_str}")
    else:
        host = host_port
        port = 5432 if dialect == 'postgres' else 3306

    password = credentials.password.get_secret_value()

    return password, db, host, port

@contextlib.asynccontextmanager
async def create_db_connection(credentials: DBConnection, dialect: str) -> AsyncGenerator[_DBWrapper, None]:
    # Parse basic path assuming format 'host:port/database' or 'host/database'
    password, db, host, port = _parse_credentials(credentials, dialect)

    if dialect == 'postgres':
        try:
            connection = await asyncpg.connect(user=credentials.user, password=password, database=db, host=host, port=port)
        except (asyncpg.exceptions.PostgresError, OSError) as e:
            raise DBConnectionError(f"Could not connect to PostgreSQL: {e}") from e

        wrapper = _DBWrapper(connection, dialect)
        try:
            yield wrapper
        finally:
            await wrapper.close()
    elif dialect == 'mysql':
        try:
            connection = await mysql.connect(user=credentials.user, password=password, database=db, host=host, port=port)
        except (mysql.connection.Error, OSError) as e:
            raise DBConnectionError(f"Could not connect to MySQL: {e}") from e

        wrapper = _DBWrapper(connection, dialect)
        try:
            yield wrapper
        finally:
            await wrapper.close()
    else:
        raise UnsupportedDialectError(f"Unsupported dialect for schema extraction: {dialect}")
