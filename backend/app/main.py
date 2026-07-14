import asyncio
from typing import Optional
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Query

from .dependencies import CacheDep
from .cache import AsyncCacheProtocol, SQLiteCache
from .format import format
from .models import AIAnalyzeResponse, AIOptimizeResponse, FormatResponse, HistoryResponse, SchemaColumn, SchemaRequest, SchemaResponse, SchemaTable, StaticAnalyzeProblem, StaticAnalyzeResponse, SQLRequest
from .analysis import Schema, analyze_sql_static, get_schema
from .gigachat_client import analyze_query_with_ai, optimize_query_with_ai
from .schema_mapper import schema_to_tables

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Init cache object for dependency injection
    cache: AsyncCacheProtocol = await SQLiteCache.create()
    app.state.cache = cache
    yield

app = FastAPI(title="SQL Assistant API", lifespan=lifespan)

@app.post("/api/v1/sql/format", response_model=FormatResponse)
async def format_sql(req: SQLRequest) -> FormatResponse:
    return await format(req)

@app.post("/api/v1/sql/analyze/static", response_model=StaticAnalyzeResponse)
async def analyze_static(req: SQLRequest, cache: CacheDep) -> StaticAnalyzeResponse:
    schema: Optional[Schema] = None
    if (req.db and req.dialect):
        schema = await get_schema(req.db, req.dialect, cache)
    problems: list[StaticAnalyzeProblem] = await asyncio.to_thread(analyze_sql_static, req.sql, req.dialect, schema)
    return StaticAnalyzeResponse(problems=problems)

@app.post("/api/v1/sql/analyze/ai", response_model=AIAnalyzeResponse)
async def analyze_ai(req: SQLRequest, cache: CacheDep) -> AIAnalyzeResponse:
    schema: Optional[Schema] = None
    if (req.db and req.dialect):
        schema = await get_schema(req.db, req.dialect, cache)
    static_problems: list[StaticAnalyzeProblem] = await asyncio.to_thread(analyze_sql_static, req.sql, req.dialect, schema)

    try:
        # Вызов GigaChat
        response: AIAnalyzeResponse = await analyze_query_with_ai(req.sql, schema, static_problems, cache)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка GigaChat: {str(e)}")

@app.post("/api/v1/sql/optimize/ai", response_model=AIOptimizeResponse)
async def optimize_ai(req: SQLRequest, cache: CacheDep) -> AIOptimizeResponse:
    schema: Optional[Schema] = None
    if (req.db and req.dialect):
        schema = await get_schema(req.db, req.dialect, cache)

    try:
        response: AIOptimizeResponse = await optimize_query_with_ai(req.sql, schema, cache)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка GigaChat: {str(e)}")

@app.post("/api/v1/sql/schema", response_model=SchemaResponse)
async def get_db_schema(req: SchemaRequest, cache: CacheDep) -> SchemaResponse:
    """Подключается к БД, извлекает схему для webview: таблицы, колонки, типы, ключи, индексы."""
    try:
        schema: Schema = await get_schema(req.db, req.dialect, cache)
        tables: list[SchemaTable] = schema_to_tables(schema)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения к БД: {str(e)}")

    return SchemaResponse(dbType=req.dialect, tables=tables)

@app.get("/api/v1/history", response_model=HistoryResponse)
async def get_history(
    cache: CacheDep,
    limit: int = Query(30, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> HistoryResponse:
    """Возвращает страницу истории рекомендаций из SQLite с пагинацией."""
    history = await cache.get_all_recommendations(limit=limit, offset=offset)
    total = await cache.count_recommendations()
    return HistoryResponse(history=history, total=total)
