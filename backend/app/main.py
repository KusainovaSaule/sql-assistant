from typing import Optional
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException

from .dependencies import CacheDep
from .cache import AsyncCacheProtocol, SQLiteCache
from .format import format
from .models import AIAnalyzeResponse, AIOptimizeResponse, FormatResponse, HistoryResponse, StaticAnalyzeProblem, StaticAnalyzeResponse, SQLRequest
from .analysis import Schema, analyze_sql_static, get_schema
from .gigachat_client import analyze_query_with_ai, optimize_query_with_ai

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
    problems: list[StaticAnalyzeProblem] = analyze_sql_static(req.sql, req.dialect, schema)
    return StaticAnalyzeResponse(problems=problems)

@app.post("/api/v1/sql/analyze/ai", response_model=AIAnalyzeResponse)
async def analyze_ai(req: SQLRequest, cache: CacheDep) -> AIAnalyzeResponse:
    schema: Optional[Schema] = None
    if (req.db and req.dialect):
        schema = await get_schema(req.db, req.dialect, cache)
        
    static_problems: list[StaticAnalyzeProblem] = analyze_sql_static(req.sql, req.dialect, schema)
    
    try:
        # Вызов GigaChat
        ai_data = await analyze_query_with_ai(req.sql, schema, static_problems)
        
        # Маппим ответ от LLM в нашу Pydantic модель
        problems = [StaticAnalyzeProblem(**p) for p in ai_data.get("problems", [])]
        
        response = AIAnalyzeResponse(
            logic_description=ai_data.get("logic_description", ""),
            problems=problems,
            recommendations=ai_data.get("recommendations", [])
        )
        
        # Сохраняем в историю SQLite
        await cache.add_recommendation("analyze_ai", req.sql, response.model_dump())
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка GigaChat: {str(e)}")

@app.post("/api/v1/sql/optimize/ai", response_model=AIOptimizeResponse)
async def optimize_ai(req: SQLRequest, cache: CacheDep) -> AIOptimizeResponse:
    schema: Optional[Schema] = None
    if (req.db and req.dialect):
        schema = await get_schema(req.db, req.dialect, cache)
        
    try:
        # Вызов GigaChat
        ai_data = await optimize_query_with_ai(req.sql, schema)
        
        response = AIOptimizeResponse(
            optimized_sql=ai_data.get("optimized_sql", req.sql),
            explanation=ai_data.get("explanation", ""),
            expected_effect=ai_data.get("expected_effect", "")
        )
        
        # Сохраняем в историю SQLite
        await cache.add_recommendation("optimize_ai", req.sql, response.model_dump())
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка GigaChat: {str(e)}")

@app.get("/api/v1/history", response_model=HistoryResponse)
async def get_history(cache: CacheDep) -> HistoryResponse:
    """Возвращает сохраненную в SQLite историю предыдущих рекомендаций и оптимизаций."""
    history = await cache.get_all_recommendations()
    return HistoryResponse(history=history)
