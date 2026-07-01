def analyze_sql_static(sql: str):
    sql_upper = sql.upper()
    problems = []

    if "SELECT *" in sql_upper:
        problems.append({
            "code": "SELECT_STAR",
            "message": "Используется SELECT *",
            "severity": "warning",
            "recommendation": "Перечислите конкретные колонки."
        })

    if "JOIN" in sql_upper and "WHERE" not in sql_upper:
        problems.append({
            "code": "JOIN_WITHOUT_WHERE",
            "message": "JOIN без WHERE может привести к декартовому произведению.",
            "severity": "warning",
            "recommendation": "Добавьте условие соединения."
        })

    return problems
