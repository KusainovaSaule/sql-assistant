from typing import Any

from fastapi import FastAPI
import sqlglot
from .models import AIAnalyzeResponse, AIOptimizeResponse, FormatResponse, HistoryResponse, StaticAnalyzeResponse, SqlRequest
from .analysis.static_analyzer import analyze_sql_static

app = FastAPI(title="SQL Assistant API")


@app.post("/api/v1/sql/format", response_model=FormatResponse)
async def format_sql(req: SqlRequest) -> FormatResponse:
    """Статический анализ и форматирование (без LLM)."""
    try:
        formatted: str = sqlglot.transpile(req.sql, pretty=True)[0]
    except Exception as e:
        return FormatResponse(formatted_sql=req.sql, error=str(e))
    return FormatResponse(formatted_sql=formatted)

@app.post("/api/v1/sql/analyze/static", response_model=StaticAnalyzeResponse)
async def analyze_static(req: SqlRequest) -> StaticAnalyzeResponse:
    """Быстрый парсинг запроса для выявления базовых антипаттернов."""
    problems: list[dict[str, Any]] = analyze_sql_static(req.sql) # TODO: implement analyser
    return StaticAnalyzeResponse(problems=problems)

@app.post("/api/v1/sql/analyze/ai", response_model=AIAnalyzeResponse)
async def analyze_ai(req: SqlRequest) -> AIAnalyzeResponse:
    """Формирует промпт с учетом статического анализа и схемы БД, отправляет в GigaChat."""
    # TODO: Интеграция с GigaChat API
    static_problems = analyze_sql_static(req.sql)
    return AIAnalyzeResponse(
        logic_description="Здесь будет описание логики от GigaChat.",
        problems=static_problems, # Пока возвращаем статические проблемы
        recommendations=["Здесь будут рекомендации от GigaChat."]
    )

@app.post("/api/v1/sql/optimize/ai", response_model=AIOptimizeResponse)
async def optimize_ai(req: SqlRequest) -> AIOptimizeResponse:
    """Запрашивает у GigaChat переписанную версию SQL-кода с объяснениями изменений."""
    # TODO: Интеграция с GigaChat API
    return AIOptimizeResponse(
        optimized_sql="-- Оптимизированный SQL от GigaChat\n" + req.sql,
        explanation="Здесь будет объяснение изменений от GigaChat.",
        expected_effect="Здесь будет ожидаемый эффект от GigaChat."
    )

@app.get("/api/v1/history", response_model=HistoryResponse)
async def get_history() -> HistoryResponse:
    """Возвращает сохраненную в SQLite историю предыдущих рекомендаций и оптимизаций."""
    # TODO: Подключение к SQLite
    return HistoryResponse(history=[])

