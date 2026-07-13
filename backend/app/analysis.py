from sqlglot.expressions.core import Expr
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

    # Anti-pattern detection (no LLM, pure AST) — fast first layer
    problems.extend(_check_antipatterns(expression))

    return problems


def _check_antipatterns(expression: sqlglot.Expr) -> list[StaticAnalyzeProblem]:
    """Обнаружение типичных проблем производительности без обращения к БД и LLM."""
    problems: list[StaticAnalyzeProblem] = []

    # 1. SELECT * — лишние колонки, ломает покрывающие индексы
    for select in expression.find_all(exp.Select):
        for proj in select.expressions:
            is_star = isinstance(proj, exp.Star) or (
                isinstance(proj, exp.Column) and isinstance(proj.this, exp.Star)
            )
            if is_star:
                problems.append(StaticAnalyzeProblem(
                    code="SELECT_STAR",
                    message="Использование SELECT * — выбираются все колонки, включая ненужные.",
                    severity="WARNING",
                    recommendation="Перечислите только нужные колонки — снижает объём передаваемых данных и позволяет применять покрывающие индексы.",
                ))
                break

    # 2. JOIN без ON/USING — декартово произведение
    for join in expression.find_all(exp.Join):
        kind = (join.args.get("kind") or "").upper()
        method = (join.args.get("method") or "").upper()
        has_condition = join.args.get("on") is not None or bool(join.args.get("using"))
        if not has_condition and kind != "CROSS" and method != "NATURAL":
            table = join.this.name if isinstance(join.this, exp.Table) else "?"
            problems.append(StaticAnalyzeProblem(
                code="JOIN_WITHOUT_CONDITION",
                message=f"JOIN таблицы '{table}' без условия ON/USING — декартово произведение.",
                severity="ERROR",
                recommendation="Добавьте условие соединения (ON ... = ...) или используйте явный CROSS JOIN, если это намеренно.",
            ))

    # 3. UPDATE/DELETE без WHERE — затрагивает всю таблицу
    for node in expression.find_all(exp.Update, exp.Delete):
        if node.args.get("where") is None:
            op = "UPDATE" if isinstance(node, exp.Update) else "DELETE"
            problems.append(StaticAnalyzeProblem(
                code="MODIFY_WITHOUT_WHERE",
                message=f"{op} без WHERE — операция затронет все строки таблицы.",
                severity="ERROR",
                recommendation="Добавьте WHERE, чтобы ограничить область изменения. Иначе будет изменена/удалена вся таблица.",
            ))

    # 4. SELECT без WHERE при наличии FROM — полное сканирование
    if isinstance(expression, exp.Select):
        from_clause = expression.args.get("from") or expression.args.get("from_")
        has_where = expression.args.get("where") is not None
        has_limit = expression.args.get("limit") is not None
        has_agg = any(isinstance(n, exp.AggFunc) for n in expression.expressions)
        if from_clause is not None and not has_where and not has_limit and not has_agg:
            problems.append(StaticAnalyzeProblem(
                code="SELECT_WITHOUT_WHERE",
                message="SELECT без WHERE и LIMIT — полное сканирование таблицы.",
                severity="WARNING",
                recommendation="Ограничьте выборку через WHERE или LIMIT, если не нужна вся таблица целиком.",
            ))

    # 5. LIKE с ведущим '%' — индекс не используется (non-sargable)
    for like in expression.find_all(exp.Like):
        rhs = like.expression
        if isinstance(rhs, exp.Literal) and rhs.is_string and rhs.this.startswith("%"):
            problems.append(StaticAnalyzeProblem(
                code="LEADING_WILDCARD",
                message=f"LIKE '{rhs.this}' начинается с '%' — B-tree индекс не применяется.",
                severity="WARNING",
                recommendation="Избегайте ведущего '%'. Для полнотекстового поиска используйте FTS/trigram-индекс (pg_trgm) или полнотекстовый поиск.",
            ))

    # 6. Функция/выражение над колонкой в WHERE — non-sargable
    for where in expression.find_all(exp.Where):
        # Ищем бинарные операции (=, <, >, <=, >=, !=)
        for binary in where.find_all(exp.Binary):
            left: Expr = binary.left
            right: Expr = binary.right

            def is_func_on_column(node: Optional[Expr]) -> bool:
                if not node:
                    return False
                # Проверяем функции и приведение типов (CAST)
                if isinstance(node, (exp.Func, exp.Cast)):
                    return any(isinstance(arg, exp.Column) for arg in node.find_all(exp.Column))
                return False

            def is_constant(node: Optional[Expr]) -> bool:
                if not node:
                    return False
                # Константы или параметры (например, ?, :1)
                return isinstance(node, (exp.Literal, exp.Parameter))

            # Паттерн: FUNC(col) = Literal ИЛИ Literal = FUNC(col)
            if (is_func_on_column(left) and is_constant(right)) or \
               (is_func_on_column(right) and is_constant(left)):
                
                func_node: Expr = left if is_func_on_column(left) else right
                fname: str = func_node.key.upper()
                
                problems.append(StaticAnalyzeProblem(
                    code="FUNCTION_ON_COLUMN",
                    message=f"Функция {fname}(...) над колонкой сравнивается с константой — индекс по колонке не используется.",
                    severity="WARNING",
                    recommendation="Перепишите условие без функции над колонкой (перенесите вычисление на константу) либо создайте функциональный индекс.",
                ))
                break

    # 7. NOT IN — ловушка с NULL и плохая производительность на подзапросах
    for not_node in expression.find_all(exp.Not):
        if isinstance(not_node.this, exp.In):
            problems.append(StaticAnalyzeProblem(
                code="NOT_IN",
                message="Использование NOT IN — при NULL в списке даёт пустой результат и медленно на подзапросах.",
                severity="WARNING",
                recommendation="Замените на NOT EXISTS или LEFT JOIN ... WHERE ... IS NULL.",
            ))

    return problems
