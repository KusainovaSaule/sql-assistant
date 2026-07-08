import os
import json
import asyncio
from typing import Optional
from dotenv import load_dotenv
from gigachat import GigaChat
from .models import StaticAnalyzeProblem
from .analysis import Schema

load_dotenv()

def _get_giga_client() -> GigaChat:
    api_key = os.getenv("GIGACHAT_API_KEY")
    if not api_key:
        raise ValueError("GIGACHAT_API_KEY не найден в .env")
    verify_ssl_certs=False #часто нужен для обхода проблем с сертификатами Сбера
    return GigaChat(credentials=api_key, verify_ssl_certs=False)

def _build_analysis_prompt(sql: str, schema: Optional[Schema], static_problems: list[StaticAnalyzeProblem]) -> str:
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

def _build_optimize_prompt(sql: str, schema: Optional[Schema]) -> str:
    prompt = f"Оптимизируй следующий SQL-запрос:\n```sql\n{sql}\n```\n\n"
    
    if schema:
        schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
        prompt += f"Учитывай эту схему базы данных:\n{schema_str}\n\n"
    else:
        prompt += "Схема базы данных неизвестна. Оптимизируй только на основе синтаксиса.\n\n"
        
    prompt += """Дай ответ СТРОГО в формате JSON (без markdown и лишнего текста):
{
  "optimized_sql": "тут только оптимизированный SQL код",
  "explanation": "Объяснение, какие изменения внесены и почему",
  "expected_effect": "Ожидаемый эффект от оптимизации"
}"""
    return prompt

async def analyze_query_with_ai(sql: str, schema: Optional[Schema], static_problems: list[StaticAnalyzeProblem]) -> dict:
    prompt = _build_analysis_prompt(sql, schema, static_problems)
    
    def _call_giga():
        with _get_giga_client() as giga:
            response = giga.chat(prompt)
            return response.choices[0].message.content
            
    raw_response = await asyncio.to_thread(_call_giga)
    clean_json = raw_response.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)

async def optimize_query_with_ai(sql: str, schema: Optional[Schema]) -> dict:
    prompt = _build_optimize_prompt(sql, schema)
    
    def _call_giga():
        with _get_giga_client() as giga:
            response = giga.chat(prompt)
            return response.choices[0].message.content
            
    raw_response = await asyncio.to_thread(_call_giga)
    clean_json = raw_response.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)