import * as vscode from "vscode";
import {
  analyzeStatic,
  analyzeAi,
  optimizeQuery,
  formatQuery,
  getSchema,
  getHistory,
  DbConfig,
} from "./apiClient";
import { SqlAssistantPanel } from "./panel";

function getSelectedSql(editor: vscode.TextEditor): string | null {
  const selection = editor.selection;
  if (!selection.isEmpty) {
    return editor.document.getText(selection);
  }
  return editor.document.getText();
}

async function getDbConfig(context: vscode.ExtensionContext): Promise<DbConfig | undefined> {
  const cfg = vscode.workspace.getConfiguration("sqlAssistant");

  const host = cfg.get<string>("db.host");
  const port = cfg.get<number>("db.port");
  const user = cfg.get<string>("db.user");
  const database = cfg.get<string>("db.database");
  const dbType = cfg.get<string>("db.type") as DbConfig["dbType"];

  if (!host || !port || !user || !database || !dbType) {
    return undefined;
  }

  const password = await context.secrets.get("dbPassword");

  return {
    host,
    port,
    user,
    password: password || "",
    database,
    dbType,
  };
}

function getDialect(): string | undefined {
  const cfg = vscode.workspace.getConfiguration("sqlAssistant");
  return cfg.get<string>("db.dialect") || "postgres";
}

export function activate(context: vscode.ExtensionContext) {
  const setPasswordCmd = vscode.commands.registerCommand(
    "sqlAssistant.setDbPassword",
    async () => {
      const password = await vscode.window.showInputBox({
        prompt: "Введите пароль для базы данных",
        password: true,
        ignoreFocusOut: true
      });

      if (password !== undefined) {
        await context.secrets.store("dbPassword", password);
        vscode.window.showInformationMessage("Пароль от БД успешно и безопасно сохранен.");
      }
    }
  );

  context.subscriptions.push(setPasswordCmd);

  const analyzeCmd = vscode.commands.registerCommand(
    "sqlAssistant.analyzeQuery",
    async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showErrorMessage("Нет активного редактора.");
        return;
      }

      const sql = getSelectedSql(editor);
      if (!sql || sql.trim().length === 0) {
        vscode.window.showErrorMessage("Выделите SQL-запрос или откройте файл с SQL.");
        return;
      }

      const panel = SqlAssistantPanel.createOrShow(context.extensionUri);
      panel.updateState({
        mode: "analysis",
        staticResult: undefined,
        aiResult: undefined,
        error: undefined,
      });

      try {
        const dialect = getDialect();
        const staticResult = await analyzeStatic(sql, dialect);
        panel.updateState({ staticResult });

        const config = await getDbConfig(context);
        const aiResult = await analyzeAi(sql, config, dialect);
        panel.updateState({ aiResult });
      } catch (err: any) {
        panel.updateState({
          error: err?.message || "Ошибка анализа запроса.",
        });
        vscode.window.showErrorMessage(
          `Ошибка анализа запроса: ${err?.message || err}`
        );
      }
    }
  );

  const optimizeCmd = vscode.commands.registerCommand(
    "sqlAssistant.optimizeQuery",
    async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showErrorMessage("Нет активного редактора.");
        return;
      }

      const sql = getSelectedSql(editor);
      if (!sql || sql.trim().length === 0) {
        vscode.window.showErrorMessage("Выделите SQL-запрос или откройте файл с SQL.");
        return;
      }

      const panel = SqlAssistantPanel.createOrShow(context.extensionUri);
      panel.updateState({
        mode: "optimization",
        optimizeResult: undefined,
        error: undefined,
      });

      try {
        const config = await getDbConfig(context);
        const dialect = getDialect();
        const result = await optimizeQuery(sql, config, dialect);
        panel.updateState({ optimizeResult: result });
      } catch (err: any) {
        panel.updateState({
          error: err?.message || "Ошибка оптимизации запроса.",
        });
        vscode.window.showErrorMessage(
          `Ошибка оптимизации запроса: ${err?.message || err}`
        );
      }
    }
  );

  const formatCmd = vscode.commands.registerCommand(
    "sqlAssistant.formatQuery",
    async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showErrorMessage("Нет активного редактора.");
        return;
      }

      const sql = getSelectedSql(editor);
      if (!sql || sql.trim().length === 0) {
        vscode.window.showErrorMessage("Выделите SQL-запрос или откройте файл с SQL.");
        return;
      }

      try {
        const result = await formatQuery(sql);
        await editor.edit((editBuilder) => {
          const selection = editor.selection;
          if (!selection.isEmpty) {
            editBuilder.replace(selection, result.formatted_sql);
          } else {
            const fullRange = new vscode.Range(
              editor.document.positionAt(0),
              editor.document.positionAt(editor.document.getText().length)
            );
            editBuilder.replace(fullRange, result.formatted_sql);
          }
        });
      } catch (err: any) {
        vscode.window.showErrorMessage(
          `Ошибка форматирования запроса: ${err?.message || err}`
        );
      }
    }
  );

  const schemaCmd = vscode.commands.registerCommand(
    "sqlAssistant.showSchema",
    async () => {
      const panel = SqlAssistantPanel.createOrShow(context.extensionUri);
      panel.updateState({
        mode: "schema",
        schemaInfo: undefined,
        error: undefined,
      });

      try {
        const config = await getDbConfig(context);
        if (!config) {
          panel.updateState({
            error: "Не настроено подключение к БД (sqlAssistant.db.*).",
          });
          vscode.window.showErrorMessage(
            "Не настроено подключение к БД (sqlAssistant.db.*)."
          );
          return;
        }

        const schema = await getSchema(config);
        panel.updateState({ schemaInfo: schema });
      } catch (err: any) {
        panel.updateState({
          error: err?.message || "Ошибка получения схемы.",
        });
        vscode.window.showErrorMessage(
          `Ошибка получения схемы: ${err?.message || err}`
        );
      }
    }
  );

  const historyCmd = vscode.commands.registerCommand(
    "sqlAssistant.showHistory",
    async () => {
      const panel = SqlAssistantPanel.createOrShow(context.extensionUri);
      panel.updateState({
        mode: "history",
        historyResult: undefined,
        error: undefined,
      });

      try {
        const history = await getHistory(50);
        panel.updateState({ historyResult: history });
      } catch (err: any) {
        panel.updateState({
          error: err?.message || "Ошибка получения истории.",
        });
        vscode.window.showErrorMessage(
          `Ошибка получения истории: ${err?.message || err}`
        );
      }
    }
  );

  context.subscriptions.push(analyzeCmd, optimizeCmd, formatCmd, schemaCmd, historyCmd);
}

export function deactivate() {}