import * as path from 'path';
import * as vscode from 'vscode';
import { showLensnnWebviewPanel } from './webviewPanel';
import { stopLensnnServer } from './serverManager';

let statusBarItem: vscode.StatusBarItem | undefined;

export function activate(context: vscode.ExtensionContext) {
  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  statusBarItem.text = 'LensNN: Idle';
  statusBarItem.tooltip = 'LensNN extension status';
  statusBarItem.command = 'lensnn.openDashboard';
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  const disposable = vscode.commands.registerCommand('lensnn.openDashboard', async () => {
    const configuration = vscode.workspace.getConfiguration('lensnn');
    const configuredPythonPath = configuration.get<string>('pythonPath', '');
    let runsDirectory = configuration.get<string>('runsDirectory', './runs');
    const portRange = configuration.get<string>('portRange', '8700-8799');

    const workspaceFolder = vscode.workspace.workspaceFolders?.length
      ? vscode.workspace.workspaceFolders[0].uri.fsPath
      : undefined;

    if (!path.isAbsolute(runsDirectory) && workspaceFolder) {
      runsDirectory = path.join(workspaceFolder, runsDirectory);
    }

    statusBarItem!.text = 'LensNN: Starting...';
    statusBarItem!.show();

    try {
      await showLensnnWebviewPanel(
        context,
        configuredPythonPath,
        workspaceFolder,
        runsDirectory,
        portRange,
        statusBarItem!,
      );
      statusBarItem!.text = 'LensNN: Running';
      statusBarItem!.show();
    } catch (error) {
      statusBarItem!.text = 'LensNN: Error';
      statusBarItem!.show();
      vscode.window.showErrorMessage(`LensNN failed to start: ${error instanceof Error ? error.message : error}`);
    }
  });

  context.subscriptions.push(disposable);
}

export function deactivate() {
  stopLensnnServer();
  statusBarItem?.hide();
}
