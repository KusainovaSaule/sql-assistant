import asyncio

import sqlglot

from .models import FormatResponse, SqlRequest


def _transpile_sql(sql: str) -> str:
    return sqlglot.transpile(sql, pretty=True)[0]

async def format(request: SqlRequest) -> FormatResponse:
    try:
        formatted: str = await asyncio.to_thread(_transpile_sql, request.sql)
    except Exception as e:
        return FormatResponse(formatted_sql=request.sql, error=str(e))
    return FormatResponse(formatted_sql=formatted)
