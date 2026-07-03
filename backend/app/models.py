
from pydantic import BaseModel
from typing import List, Optional

class SqlRequest(BaseModel):
    sql: str
    db_schema: Optional[dict] = None # NOTE: Maybe replace with DB address and credentials?

class FormatResponse(BaseModel):
    formatted_sql: str
    error: Optional[str] = None

class StaticAnalyzeResponse(BaseModel):
    problems: List[dict]

class AIAnalyzeResponse(BaseModel):
    logic_description: str
    problems: List[dict]
    recommendations: List[str]

class AIOptimizeResponse(BaseModel):
    optimized_sql: str
    explanation: str
    expected_effect: str

class HistoryResponse(BaseModel):
    history: List[dict]

