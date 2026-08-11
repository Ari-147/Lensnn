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
exports.activate = activate;
exports.deactivate = deactivate;
const path = __importStar(require("path"));
const vscode = __importStar(require("vscode"));
const webviewPanel_1 = require("./webviewPanel");
const serverManager_1 = require("./serverManager");
let statusBarItem;
function activate(context) {
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.text = 'LensNN: Idle';
    statusBarItem.tooltip = 'LensNN extension status';
    statusBarItem.command = 'lensnn.openDashboard';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
    const disposable = vscode.commands.registerCommand('lensnn.openDashboard', async () => {
        const configuration = vscode.workspace.getConfiguration('lensnn');
        const pythonPath = configuration.get('pythonPath', 'python');
        let runsDirectory = configuration.get('runsDirectory', './runs');
        const portRange = configuration.get('portRange', '8700-8799');
        if (!path.isAbsolute(runsDirectory) && vscode.workspace.workspaceFolders?.length) {
            runsDirectory = path.join(vscode.workspace.workspaceFolders[0].uri.fsPath, runsDirectory);
        }
        statusBarItem.text = 'LensNN: Starting...';
        statusBarItem.show();
        try {
            await (0, webviewPanel_1.createLensnnWebviewPanel)(context, pythonPath, runsDirectory, portRange, statusBarItem);
            statusBarItem.text = 'LensNN: Running';
            statusBarItem.show();
        }
        catch (error) {
            statusBarItem.text = 'LensNN: Error';
            statusBarItem.show();
            vscode.window.showErrorMessage(`LensNN failed to start: ${error instanceof Error ? error.message : error}`);
        }
    });
    context.subscriptions.push(disposable);
}
function deactivate() {
    (0, serverManager_1.stopLensnnServer)();
    statusBarItem?.hide();
}
//# sourceMappingURL=extension.js.map