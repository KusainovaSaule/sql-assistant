import * as vscode from "vscode";

export interface PanelState {
  mode: "analysis" | "optimization" | "schema" | "history";
  staticResult?: any;
  aiResult?: any;
  optimizeResult?: any;
  schemaInfo?: any;
  historyResult?: any;
  error?: string;
}

export class SqlAssistantPanel {
  public static currentPanel: SqlAssistantPanel | undefined;
  public onRequestHistoryPage?: (offset: number) => void;
  private readonly panel: vscode.WebviewPanel;
  private disposables: vscode.Disposable[] = [];
  private state: PanelState = { mode: "analysis" };

  public static createOrShow(extensionUri: vscode.Uri) {
    const column = vscode.ViewColumn.Beside;

    if (SqlAssistantPanel.currentPanel) {
      SqlAssistantPanel.currentPanel.panel.reveal(column);
      return SqlAssistantPanel.currentPanel;
    }

    const panel = vscode.window.createWebviewPanel(
      "sqlAssistantPanel",
      "SQL Assistant",
      column,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
      }
    );

    SqlAssistantPanel.currentPanel = new SqlAssistantPanel(panel, extensionUri);
    return SqlAssistantPanel.currentPanel;
  }

  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
    this.panel = panel;

    const webview = this.panel.webview;

    const cssUri = webview.asWebviewUri(
      vscode.Uri.joinPath(extensionUri, "media", "panel.css")
    );
    const jsUri = webview.asWebviewUri(
      vscode.Uri.joinPath(extensionUri, "media", "panel.js")
    );

    this.panel.webview.html = this.getHtml(cssUri, jsUri);

    this.panel.onDidDispose(() => this.dispose(), null, this.disposables);

    this.panel.webview.onDidReceiveMessage(
      (message) => {
        if (message.command === "applyOptimizedQuery") {
          this.applyOptimizedQuery(message.text);
        } else if (message.command === "loadHistoryPage") {
          this.onRequestHistoryPage?.(message.offset);
        }
      },
      null,
      this.disposables
    );
  }

  public updateState(newState: Partial<PanelState>) {
    this.state = { ...this.state, ...newState };
    this.panel.webview.postMessage({
      command: "updateState",
      state: this.state,
    });
  }

  private applyOptimizedQuery(text: string) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showErrorMessage("Нет активного редактора.");
      return;
    }

    editor.edit((editBuilder) => {
      const selection = editor.selection;
      if (!selection.isEmpty) {
        editBuilder.replace(selection, text);
      } else {
        editBuilder.insert(selection.active, text);
      }
    });
  }

  private getHtml(cssUri: vscode.Uri, jsUri: vscode.Uri): string {
    const webview = this.panel.webview;

    return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />

  <meta http-equiv="Content-Security-Policy"
        content="
          default-src 'none';
          img-src ${webview.cspSource} https:;
          script-src ${webview.cspSource};
          style-src ${webview.cspSource} 'unsafe-inline';
        ">

  <title>SQL Assistant</title>
  <link rel="stylesheet" href="${cssUri}">
</head>

<body>
  <div class="container">
    <div class="tabs">
      <div class="tab active" data-mode="analysis">Analysis</div>
      <div class="tab" data-mode="optimization">Optimization</div>
      <div class="tab" data-mode="schema">Schema</div>
      <div class="tab" data-mode="history">History</div>
    </div>

    <div id="error" class="error" style="display:none;"></div>

    <div id="analysis-section" class="section">
      <h3>Static analysis</h3>
      <div id="static-summary"></div>
      <ul id="static-issues"></ul>
      <ul id="static-recommendations"></ul>

      <h3>AI analysis</h3>
      <div id="ai-summary"></div>
      <ul id="ai-issues"></ul>
      <ul id="ai-recommendations"></ul>
      <div id="ai-explanation"></div>
    </div>

    <div id="optimization-section" class="section" style="display:none;">
      <h3>Optimized SQL</h3>
      <pre id="optimized-sql"></pre>

      <h3>Explanation</h3>
      <div id="optimization-explanation"></div>

      <h3>Expected effect</h3>
      <div id="optimization-effect"></div>

      <div class="button-row">
        <button id="apply-optimized">Apply optimized query</button>
        <button id="copy-optimized" class="secondary">Copy to clipboard</button>
      </div>
    </div>

    <div id="schema-section" class="section" style="display:none;">
      <h3>Database schema</h3>
      <div id="schema-dbtype"></div>
      <div id="schema-tables"></div>
    </div>

    <div id="history-section" class="section" style="display:none;">
      <h3>Query History</h3>
      <div id="history-list"></div>
      <div id="history-pager" class="pager"></div>
    </div>
  </div>

  <script src="${jsUri}"></script>
</body>
</html>
    `;
  }

  public dispose() {
    SqlAssistantPanel.currentPanel = undefined;
    this.panel.dispose();
    this.disposables.forEach((d) => d.dispose());
  }
}
