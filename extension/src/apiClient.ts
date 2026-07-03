export interface DbConfig {
  host: string;
  port: number;
  user: string;
  password: string;
  database: string;
  dbType: "postgres" | "mysql" | "clickhouse";
}

const BASE_URL = "http://127.0.0.1:8000/api/v1";

async function post(url: string, body: any) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP ${response.status}: ${text}`);
  }

  return response.json();
}

export async function analyzeStatic(sql: string) {
  return post(`${BASE_URL}/analyze/static`, { query: sql });
}

export async function analyzeAi(sql: string, config?: DbConfig) {
  return post(`${BASE_URL}/analyze/ai`, { query: sql, config });
}

export async function optimizeQuery(sql: string, config?: DbConfig) {
  return post(`${BASE_URL}/optimize`, { query: sql, config });
}

export async function formatQuery(sql: string) {
  return post(`${BASE_URL}/format`, { query: sql });
}

export async function getSchema(config: DbConfig) {
  return post(`${BASE_URL}/schema`, { config });
}
