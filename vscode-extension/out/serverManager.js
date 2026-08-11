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
exports.findFreePort = findFreePort;
exports.startLensnnServer = startLensnnServer;
exports.stopLensnnServer = stopLensnnServer;
const http = __importStar(require("http"));
const net = __importStar(require("net"));
const path = __importStar(require("path"));
const child_process_1 = require("child_process");
const vscode = __importStar(require("vscode"));
let serverProcess = null;
let outputChannel = null;
function getOutputChannel() {
    if (!outputChannel) {
        outputChannel = vscode.window.createOutputChannel('LensNN Server');
    }
    return outputChannel;
}
function parsePortRange(portRange) {
    const parts = portRange.split('-').map((part) => parseInt(part, 10));
    if (parts.length !== 2 || parts.some((value) => Number.isNaN(value))) {
        throw new Error(`Invalid portRange: ${portRange}`);
    }
    return [parts[0], parts[1]];
}
async function isPortFree(port) {
    return new Promise((resolve) => {
        const server = net.createServer();
        server.once('error', () => {
            resolve(false);
        });
        server.once('listening', () => {
            server.close(() => resolve(true));
        });
        server.listen(port, '127.0.0.1');
    });
}
async function findFreePort(portRange) {
    const [start, end] = parsePortRange(portRange);
    for (let port = start; port <= end; port += 1) {
        if (await isPortFree(port)) {
            return port;
        }
    }
    throw new Error(`No free port found in range ${portRange}`);
}
function waitForHealthCheck(url, timeoutMs = 10000) {
    const start = Date.now();
    return new Promise((resolve, reject) => {
        const attempt = () => {
            const request = http.get(url, (response) => {
                response.resume();
                if (response.statusCode === 200) {
                    resolve();
                }
                else if (Date.now() - start > timeoutMs) {
                    reject(new Error('Health check timed out'));
                }
                else {
                    setTimeout(attempt, 200);
                }
            });
            request.on('error', () => {
                if (Date.now() - start > timeoutMs) {
                    reject(new Error('Health check timed out'));
                }
                else {
                    setTimeout(attempt, 200);
                }
            });
        };
        attempt();
    });
}
async function startLensnnServer(pythonPath, runsDirectory, portRange) {
    if (serverProcess) {
        stopLensnnServer();
    }
    const port = await findFreePort(portRange);
    const args = ['-m', 'lensnn', 'serve', runsDirectory, '--port', port.toString()];
    const outputChannel = getOutputChannel();
    outputChannel.appendLine(`Starting LensNN server: ${pythonPath} ${args.join(' ')}`);
    outputChannel.show(true);
    serverProcess = (0, child_process_1.spawn)(pythonPath, args, {
        cwd: path.isAbsolute(runsDirectory) ? runsDirectory : process.cwd(),
        env: process.env,
        stdio: ['ignore', 'pipe', 'pipe'],
    });
    serverProcess.stdout?.on('data', (chunk) => {
        outputChannel.appendLine(chunk.toString().trim());
    });
    serverProcess.stderr?.on('data', (chunk) => {
        outputChannel.appendLine(chunk.toString().trim());
    });
    serverProcess.on('exit', (code, signal) => {
        outputChannel.appendLine(`LensNN server exited (${code ?? 'unknown'}, ${signal ?? 'no signal'})`);
        if (serverProcess) {
            serverProcess = null;
        }
    });
    try {
        await waitForHealthCheck(`http://127.0.0.1:${port}/health`);
    }
    catch (error) {
        stopLensnnServer();
        throw error;
    }
    return { port, runsDirectory };
}
function stopLensnnServer() {
    if (serverProcess) {
        const outputChannel = getOutputChannel();
        outputChannel.appendLine('Stopping LensNN server');
        try {
            serverProcess.kill();
        }
        catch {
            // ignore
        }
        serverProcess = null;
    }
}
//# sourceMappingURL=serverManager.js.map