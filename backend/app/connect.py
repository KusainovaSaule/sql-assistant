import contextlib
from typing import Any, AsyncGenerator

import asyncpg
import mysql.connector.aio as mysql

from .models import DBConnection


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

    async def close(self) -> None:
        await self.connection.close()

@contextlib.asynccontextmanager
async def create_db_connection(credentials: DBConnection, dialect: str) -> AsyncGenerator[_DBWrapper, None]:
    # Parse basic path assuming format 'host:port/database' or 'host/database'
    parts: list[str] = credentials.path.split('/')
    host_port = parts[0]
    db = parts[1] if len(parts) > 1 else ''
    
    if ':' in host_port:
        host, port_str = host_port.split(':')
        port = int(port_str)
    else:
        host = host_port
        port = 5432 if dialect == 'postgres' else 3306

    password = credentials.password.get_secret_value()

    if dialect == 'postgres':
        connection = await asyncpg.connect(user=credentials.user, password=password, database=db, host=host, port=port)
        wrapper = _DBWrapper(connection, dialect)
        try:
            yield wrapper
        finally:
            await wrapper.close()
    elif dialect == 'mysql':
        connection = await mysql.connect(user=credentials.user, password=password, database=db, host=host, port=port)
        wrapper = _DBWrapper(connection, dialect)
        try:
            yield wrapper
        finally:
            await wrapper.close()
    else:
        raise ValueError(f"Unsupported dialect for schema extraction: {dialect}")