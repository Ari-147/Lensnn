import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
  const disposable = vscode.commands.registerCommand('lensnn.openDashboard', () => {
    vscode.window.showInformationMessage('LensNN: Open Dashboard invoked');
  });

  context.subscriptions.push(disposable);
}

export function deactivate() {
  // The extension has no background resources to dispose yet.
}
