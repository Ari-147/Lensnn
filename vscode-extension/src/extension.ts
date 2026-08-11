import * as path from 'path';
import * as vscode from 'vscode';
import { createLensnnWebviewPanel } from './webviewPanel';
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
    const pythonPath = configuration.get<string>('pythonPath', 'python');
    let runsDirectory = configuration.get<string>('runsDirectory', './runs');
    const portRange = configuration.get<string>('portRange', '8700-8799');

    if (!path.isAbsolute(runsDirectory) && vscode.workspace.workspaceFolders?.length) {
      runsDirectory = path.join(vscode.workspace.workspaceFolders[0].uri.fsPath, runsDirectory);
    }

    statusBarItem!.text = 'LensNN: Starting...';
    statusBarItem!.show();

    try {
      await createLensnnWebviewPanel(context, pythonPath, runsDirectory, portRange, statusBarItem!);
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
