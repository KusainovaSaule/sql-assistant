from fastapi import FastAPI
from pydantic import BaseModel
from app.analysis.static_analyzer import analyze_sql_static

app = FastAPI()

class AnalyzeRequest(BaseModel):
    sql: str

class AnalyzeResponse(BaseModel):
    logic_description: str
    problems: list
    recommendations: list

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    problems = analyze_sql_static(req.sql)
    recommendations = [p["recommendation"] for p in problems]

    return AnalyzeResponse(
        logic_description="Статическое описание логики запроса.",
        problems=problems,
        recommendations=recommendations
    )
