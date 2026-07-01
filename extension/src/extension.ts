import * as vscode from "vscode";

export function activate(context: vscode.ExtensionContext) {
  const analyzeCmd = vscode.commands.registerCommand(
    "sqlAssistant.analyzeQuery",
    () => {
      vscode.window.showInformationMessage("Analyze Query triggered!");
    }
  );

  context.subscriptions.push(analyzeCmd);
}

export function deactivate() {}
