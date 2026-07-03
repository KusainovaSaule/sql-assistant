
from pydantic import BaseModel, SecretStr
from typing import List, Optional

class DBConnection(BaseModel):
    address: str
    user: str
    password: SecretStr

class SQLRequest(BaseModel):
    sql: str
    dialect: Optional[str] = None
    db: Optional[DBConnection] = None

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

