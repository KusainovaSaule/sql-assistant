import * as vscode from "vscode";

export class SqlPanel {
  public static current: SqlPanel | undefined;
  private readonly panel: vscode.WebviewPanel;

  private constructor(panel: vscode.WebviewPanel) {
    this.panel = panel;
    this.panel.webview.html = this.getHtml();
  }

  static createOrShow() {
    const column = vscode.ViewColumn.Beside;

    if (SqlPanel.current) {
      SqlPanel.current.panel.reveal(column);
      return SqlPanel.current;
    }

    const panel = vscode.window.createWebviewPanel(
      "sqlAssistant",
      "SQL Assistant",
      column,
      { enableScripts: true }
    );

    SqlPanel.current = new SqlPanel(panel);
    return SqlPanel.current;
  }

  update(result: any) {
    this.panel.webview.postMessage({ type: "result", payload: result });
  }

  private getHtml() {
    return `
      <html>
      <body>
        <h2>SQL Analysis</h2>
        <div id="content"></div>
        <script>
          const vscode = acquireVsCodeApi();
          window.addEventListener("message", event => {
            const res = event.data.payload;
            document.getElementById("content").innerHTML =
              "<pre>" + JSON.stringify(res, null, 2) + "</pre>";
          });
        </script>
      </body>
      </html>
    `;
  }
}
