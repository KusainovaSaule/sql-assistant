# Setup and Running
## Python version
**3.14**
## Install uv package manager (Recommended)
[Instruction](https://docs.astral.sh/uv/getting-started/installation/#pypi)
## Install dependencies
```bash
uv sync
```

## Run the application
```bash
uv run fastapi dev
```
The API will be available at `http://127.0.0.1:8000`.

# API testing
Open "./api_testing" directory with Restfox.

# API Endpoints

## `POST /api/v1/sql/format`
Static analysis and formatting (without LLM).
* **Input** (`SQLRequest`):
  * `sql` (string, required): The SQL query string.
  * `dialect` (string, optional): SQL dialect.
  * `db` (object, optional): Database connection details (`path`, `user`, `password`).
* **Output** (`FormatResponse`):
  * `formatted_sql` (string): The formatted SQL query.
  * `error` (string, optional): Error message if formatting fails.

## `POST /api/v1/sql/analyze/static`
Fast parsing of the query to identify basic anti-patterns.
* **Input** (`SQLRequest`):
  * `sql` (string, required): The SQL query string.
  * `dialect` (string, optional): SQL dialect.
  * `db` (object, optional): Database connection details (`path`, `user`, `password`).
* **Output** (`StaticAnalyzeResponse`):
  * `problems` (array of objects): List of identified problems/anti-patterns.

## `POST /api/v1/sql/analyze/ai`
Generates a prompt considering static analysis and DB connection, sends to GigaChat for analysis.
* **Input** (`SQLRequest`):
  * `sql` (string, required): The SQL query string.
  * `dialect` (string, optional): SQL dialect.
  * `db` (object, optional): Database connection details (`path`, `user`, `password`).
* **Output** (`AIAnalyzeResponse`):
  * `logic_description` (string): Description of the query logic from the LLM.
  * `problems` (array of objects): List of identified problems.
  * `recommendations` (array of strings): List of recommendations for improvement.

## `POST /api/v1/sql/optimize/ai`
Requests a rewritten, optimized version of the SQL code from GigaChat with explanations.
* **Input** (`SQLRequest`):
  * `sql` (string, required): The SQL query string.
  * `dialect` (string, optional): SQL dialect.
  * `db` (object, optional): Database connection details (`path`, `user`, `password`).
* **Output** (`AIOptimizeResponse`):
  * `optimized_sql` (string): The optimized SQL query.
  * `explanation` (string): Explanation of the changes made.
  * `expected_effect` (string): The expected effect of the optimization.

## `GET /api/v1/history`
Returns the saved history of previous recommendations and optimizations from SQLite.
* **Input**: None
* **Output** (`HistoryResponse`):
  * `history` (array of objects): List of historical recommendation/optimization records.
