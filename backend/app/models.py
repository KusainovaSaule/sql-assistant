
from pydantic import BaseModel, SecretStr
from typing import List, Optional

class DBConnection(BaseModel):
    path: str
    user: str
    password: SecretStr

class SQLRequest(BaseModel):
    sql: str
    dialect: Optional[str] = None
    db: Optional[DBConnection] = None

class FormatResponse(BaseModel):
    formatted_sql: str
    error: Optional[str] = None

class StaticAnalyzeProblem(BaseModel):
    code: str
    message: str
    severity: str
    recommendation: str

class StaticAnalyzeResponse(BaseModel):
    problems: List[StaticAnalyzeProblem]

class AIAnalyzeResponse(BaseModel):
    logic_description: str
    problems: List[StaticAnalyzeProblem]
    recommendations: List[str]

class AIOptimizeResponse(BaseModel):
    optimized_sql: str
    explanation: str
    expected_effect: str

class HistoryResponse(BaseModel):
    history: List[dict]
    total: int = 0
