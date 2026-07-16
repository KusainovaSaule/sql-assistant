from pydantic import ValidationError
import os
import json
from typing import Any, Optional
from dotenv import load_dotenv
from gigachat import ChatCompletion, GigaChat

from .cache import AsyncCacheProtocol
from .models import AIAnalyzeResponse, AIOptimizeResponse, StaticAnalyzeProblem
from .analysis import Schema


class AIServiceError(Exception): pass
class AIResponseParseError(Exception): pass

load_dotenv()

def _get_verify_ssl_certs_option() -> bool:
    val = os.getenv("VERIFY_SSL_CERTS", "true").strip().lower()
    return val not in ("false", "0", "no", "off")

def _get_giga_client() -> GigaChat:
    api_key = os.getenv("GIGACHAT_API_KEY")
    verify_ssl_certs: bool = _get_verify_ssl_certs_option()

    if not api_key:
        raise ValueError("GIGACHAT_API_KEY не найден в .env")
    return GigaChat(credentials=api_key, verify_ssl_certs=verify_ssl_certs)

def _build_analysis_prompt(sql: str, schema: Optional[Schema], static_problems: list[StaticAnalyzeProblem],) -> str:
    prompt = f"Проанализируй следующий SQL-запрос:\n```sql\n{sql}\n```\n\n"

    if schema:
        schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
        prompt += f"Схема базы данных (таблицы и колонки):\n{schema_str}\n\n"
    else:
        prompt += "Схема базы данных неизвестна. Анализируй только по тексту запроса.\n\n"

    if static_problems:
        problems_str = "\n".join([f"- {p.message}" for p in static_problems])
        prompt += f"Уже найденные статические проблемы:\n{problems_str}\n\n"
        
    prompt += """Дай ответ СТРОГО в формате JSON (без markdown и лишнего текста):
{
  "logic_description": "Краткое описание того, что делает запрос",
  "problems": [{"code": "ISSUE_CODE", "message": "Описание проблемы", "severity": "WARNING", "recommendation": "Как исправить"}],
  "recommendations": ["Общая рекомендация 1", "Общая рекомендация 2"]
}"""
    return prompt

def _build_optimize_prompt(sql: str, schema: Optional[Schema], schema_meta: Optional[str] = None) -> str:
    prompt = f"Оптимизируй следующий SQL-запрос:\n```sql\n{sql}\n```\n\n"

    if schema:
        schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
        prompt += f"Учитывай эту схему базы данных:\n{schema_str}\n\n"
    else:
        prompt += "Схема базы данных неизвестна. Оптимизируй только на основе синтаксиса.\n\n"

    if schema_meta:
        prompt += f"Существующие первичные ключи и индексы (не предлагай уже имеющиеся):\n{schema_meta}\n\n"

    prompt += """Дай ответ СТРОГО в формате JSON (без markdown и лишнего текста):
{
  "optimized_sql": "тут только оптимизированный SQL код",
  "explanation": "Объяснение, какие изменения внесены и почему",
  "expected_effect": "Ожидаемый эффект от оптимизации"
}"""
    return prompt

async def analyze_query_with_ai(sql: str, schema: Optional[Schema], static_problems: list[StaticAnalyzeProblem],
                                cache: AsyncCacheProtocol) -> AIAnalyzeResponse:
    cached_response: Optional[dict[str, Any]] = await cache.get_recommendation("analyze_ai", sql)

    if (cached_response is not None):
        return AIAnalyzeResponse.model_validate(cached_response)

    prompt = _build_analysis_prompt(sql, schema, static_problems)
    
    async def _call_giga() -> str:
        try:
            with _get_giga_client() as giga:
                response: ChatCompletion = await giga.achat(prompt)
                return response.choices[0].message.content
        except ValueError:
            raise
        except Exception as e:
            raise AIServiceError(f"GigaChat request failed: {e}") from e
            
    raw_response = await _call_giga()
    clean_json = raw_response.strip().replace("```json", "").replace("```", "").strip()

    try:
        ai_data: dict[str, Any] = json.loads(clean_json)

        problems = [StaticAnalyzeProblem(**p) for p in ai_data.get("problems", [])]
            
        response = AIAnalyzeResponse(
            logic_description=ai_data.get("logic_description", ""),
            problems=problems,
            recommendations=ai_data.get("recommendations", [])
        )
    except (json.JSONDecodeError, ValidationError, TypeError) as e:
        raise AIResponseParseError(f"GigaChat returned an unexpected response format: {e}") from e
    
    # Сохраняем в историю SQLite
    await cache.add_recommendation("analyze_ai", sql, response.model_dump())

    return response


async def optimize_query_with_ai(sql: str, schema: Optional[Schema], cache: AsyncCacheProtocol,
                                 schema_meta: Optional[str] = None) -> AIOptimizeResponse:
    cached_response: Optional[dict[str, Any]] = await cache.get_recommendation("optimize_ai", sql)

    if (cached_response is not None):
        return AIOptimizeResponse.model_validate(cached_response)

    prompt = _build_optimize_prompt(sql, schema, schema_meta)
    
    async def _call_giga() -> str:
        with _get_giga_client() as giga:
            response: ChatCompletion = await giga.achat(prompt)
            return response.choices[0].message.content
            
    raw_response = await _call_giga()
    clean_json = raw_response.strip().replace("```json", "").replace("```", "").strip()

    ai_data = json.loads(clean_json)

    response = AIOptimizeResponse(
        optimized_sql=ai_data.get("optimized_sql", sql),
        explanation=ai_data.get("explanation", ""),
        expected_effect=ai_data.get("expected_effect", "")
    )
    
    # Сохраняем в историю SQLite
    await cache.add_recommendation("optimize_ai", sql, response.model_dump())
    return response
