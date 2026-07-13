from typing import Optional, Sequence, cast

import sqlglot
from sqlglot.errors import ParseError, OptimizeError
from sqlglot.optimizer.qualify import qualify
import sqlglot.expressions as exp

from .cache import AsyncCacheProtocol

from .connect import create_db_connection
from .models import DBConnection, SchemaColumn, SchemaTable, StaticAnalyzeProblem


type Column = dict[str, str]
type Schema = dict[str, Column]

async def get_schema(credentials: DBConnection, dialect: str, cache: AsyncCacheProtocol) -> Schema:
    schema: Optional[Schema] = await cache.get_schema(credentials, dialect)

    if (schema is not None):
        return schema
    
    schema = {}
    
    async with create_db_connection(credentials, dialect) as db_wrapper:
        columns: Sequence[tuple[str, str, str]] = await db_wrapper.fetch_schema_columns()
        for table, column, dtype in columns:
            if table not in schema:
                schema[table] = {}
            schema[table][column] = dtype
    
    await cache.set_schema(credentials, dialect, schema)

    return schema

async def get_schema_detailed(credentials: DBConnection, dialect: str,
                              cache: AsyncCacheProtocol) -> list[SchemaTable]:
    """Detailed schema for the UI/GigaChat: columns + primary keys + indexes.

    Cached with the same TTL as the simple schema so repeated Show Schema /
    AI calls don't hit the DB every time.
    """
    cached: Optional[list[dict]] = await cache.get_detailed_schema(credentials, dialect)
    if cached is not None:
        return [SchemaTable.model_validate(t) for t in cached]

    async with create_db_connection(credentials, dialect) as db_wrapper:
        columns: Sequence[tuple[str, str, str]] = await db_wrapper.fetch_schema_columns()
        primary_keys: set[tuple[str, str]] = await db_wrapper.fetch_primary_keys()
        indexed: set[tuple[str, str]] = await db_wrapper.fetch_indexed_columns()

    tables: dict[str, list[SchemaColumn]] = {}
    for table, column, dtype in columns:
        tables.setdefault(table, []).append(
            SchemaColumn(
                name=column,
                type=dtype,
                isPrimaryKey=(table, column) in primary_keys,
                isIndexed=(table, column) in indexed,
            )
        )

    result = [SchemaTable(name=name, columns=cols) for name, cols in tables.items()]
    await cache.set_detailed_schema(credentials, dialect, [t.model_dump() for t in result])
    return result

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
    if schema is not None and expression:
        try:
            # Validate that tables exist
            
            for table in expression.find_all(exp.Table):
                table_name = table.name
                if table_name not in schema:
                    raise OptimizeError(f"Table '{table_name}' does not exist in the schema.")

            # Find column-level issues
            expression = qualify(expression, schema=cast(dict[str, object], schema), dialect=dialect)
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
