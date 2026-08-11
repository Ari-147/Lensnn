import * as vscode from 'vscode';
import { startLensnnServer, stopLensnnServer } from './serverManager';

export async function createLensnnWebviewPanel(
  context: vscode.ExtensionContext,
  pythonPath: string,
  runsDirectory: string,
  portRange: string,
  statusBarItem: vscode.StatusBarItem,
) {
  const { port } = await startLensnnServer(pythonPath, runsDirectory, portRange);
  const origin = `http://127.0.0.1:${port}`;
  const panel = vscode.window.createWebviewPanel(
    'lensnnDashboard',
    'LensNN',
    vscode.ViewColumn.One,
    {
      enableScripts: true,
      retainContextWhenHidden: true,
    },
  );

  panel.webview.html = getWebviewHtml(origin);

  panel.onDidDispose(() => {
    stopLensnnServer();
    statusBarItem.text = 'LensNN: Stopped';
    statusBarItem.show();
  }, null, context.subscriptions);
}

function getWebviewHtml(origin: string): string {
  return `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; frame-src ${origin}; connect-src ${origin}; img-src ${origin} data:; style-src 'unsafe-inline';" />
    <title>LensNN</title>
    <style>
      html, body {
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
      }
      iframe {
        border: none;
        width: 100%;
        height: 100%;
      }
    </style>
  </head>
  <body>
    <iframe src="${origin}"></iframe>
  </body>
</html>`;
}
