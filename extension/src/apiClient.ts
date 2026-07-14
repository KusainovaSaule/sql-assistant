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

async function get(url: string) {
  const response = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP ${response.status}: ${text}`);
  }

  return response.json();
}

export async function analyzeStatic(sql: string, dialect?: string) {
  return post(`${BASE_URL}/sql/analyze/static`, { sql, dialect });
}

export async function analyzeAi(sql: string, config?: DbConfig, dialect?: string) {
  const body: any = { sql, dialect };
  if (config) {
    body.db = {
      path: `${config.host}:${config.port}/${config.database}`,
      user: config.user,
      password: config.password,
    };
  }
  return post(`${BASE_URL}/sql/analyze/ai`, body);
}

export async function optimizeQuery(sql: string, config?: DbConfig, dialect?: string) {
  const body: any = { sql, dialect };
  if (config) {
    body.db = {
      path: `${config.host}:${config.port}/${config.database}`,
      user: config.user,
      password: config.password,
    };
  }
  return post(`${BASE_URL}/sql/optimize/ai`, body);
}

export async function formatQuery(sql: string) {
  return post(`${BASE_URL}/sql/format`, { sql });
}

export async function getSchema(config: DbConfig) {
  return post(`${BASE_URL}/sql/schema`, { db: config });
}

export async function getHistory(limit: number = 30, offset: number = 0) {
  return get(`${BASE_URL}/history?limit=${limit}&offset=${offset}`);
}