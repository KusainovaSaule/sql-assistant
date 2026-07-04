from typing import Optional

import sqlglot
from sqlglot.errors import ParseError, OptimizeError
from sqlglot import optimizer

from .models import DBConnection, StaticAnalyzeProblem


type Column = dict[str, str]
type Schema = dict[str, Column]    

async def get_schema(credentials: DBConnection, dialect: str) -> Schema:
    raise NotImplementedError

def analyze_sql_static(sql: str, dialect: Optional[str], schema: Optional[Schema] = None) -> list[StaticAnalyzeProblem]:
    problems: list[StaticAnalyzeProblem] = []
    
    try:
        # Syntax validation (AST parsing)
        expression: sqlglot.Expr = sqlglot.parse_one(sql, read=dialect)
    except ParseError as e:
        for error in e.errors:
            problems.append(
                StaticAnalyzeProblem(
                    code="SYNTAX_ERROR",
                    message=f"Syntax error at line {error.get('line')}, col {error.get('col')}: {error.get('description')}",
                    severity="ERROR",
                    recommendation="Check SQL syntax near the reported line and column."
                )
            )
        return problems

    # Semantic validation (if schema is provided)
    if schema and expression:
        try:
            optimizer.optimize(expression, schema=schema, dialect=dialect)
        except OptimizeError as e:
            problems.append(
                StaticAnalyzeProblem(
                    code="SEMANTIC_ERROR",
                    message=f"Semantic error: {str(e)}",
                    severity="ERROR",
                    recommendation="Ensure tables and columns exist in the schema and are unambiguously referenced."
                )
            )

    return problems
