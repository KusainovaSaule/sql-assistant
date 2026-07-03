import * as vscode from "vscode";

export interface PanelState {
  mode: "analysis" | "optimization" | "schema";
  staticResult?: any;
  aiResult?: any;
  optimizeResult?: any;
  schemaInfo?: any;
  error?: string;
}

export class SqlAssistantPanel {
  public static currentPanel: SqlAssistantPanel | undefined;
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
    const htmlUri = webview.asWebviewUri(
      vscode.Uri.joinPath(extensionUri, "media", "panel.html")
    );

    this.panel.webview.html = this.getHtml(htmlUri);

    this.panel.onDidDispose(() => this.dispose(), null, this.disposables);

    this.panel.webview.onDidReceiveMessage(
      (message) => {
        if (message.command === "applyOptimizedQuery") {
          this.applyOptimizedQuery(message.text);
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

  private getHtml(htmlUri: vscode.Uri): string {
    // panel.html будет загружаться через src в WebView
    return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>SQL Assistant</title>
  <link rel="stylesheet" href="${htmlUri.toString().replace("panel.html", "panel.css")}">
</head>
<body>
  <div id="root"></div>
  <script src="${htmlUri.toString().replace("panel.html", "panel.js")}"></script>
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
