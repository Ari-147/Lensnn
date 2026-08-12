"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.showLensnnWebviewPanel = showLensnnWebviewPanel;
const vscode = __importStar(require("vscode"));
const serverManager_1 = require("./serverManager");
let currentPanel;
async function showLensnnWebviewPanel(context, pythonPath, runsDirectory, portRange, statusBarItem) {
    // Re-running the command should surface the existing dashboard, not
    // spawn a second server and orphan the first panel's server out from
    // under it.
    if (currentPanel) {
        currentPanel.reveal(vscode.ViewColumn.One);
        return;
    }
    const { port } = await (0, serverManager_1.startLensnnServer)(pythonPath, runsDirectory, portRange);
    const origin = `http://127.0.0.1:${port}`;
    const panel = vscode.window.createWebviewPanel('lensnnDashboard', 'LensNN', vscode.ViewColumn.One, {
        enableScripts: true,
        retainContextWhenHidden: true,
    });
    panel.webview.html = getWebviewHtml(origin);
    currentPanel = panel;
    panel.onDidDispose(() => {
        currentPanel = undefined;
        (0, serverManager_1.stopLensnnServer)();
        statusBarItem.text = 'LensNN: Stopped';
        statusBarItem.show();
    }, null, context.subscriptions);
}
function getWebviewHtml(origin) {
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
//# sourceMappingURL=webviewPanel.js.map