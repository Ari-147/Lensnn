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
            // Per-attempt socket timeout: an ordinary refused connection fails
            // fast via the 'error' event, but a hung (not refused) connection
            // would otherwise never fire either callback and could stall past
            // the intended overall timeoutMs.
            const request = http.get(url, { timeout: 1500 }, (response) => {
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
            request.on('timeout', () => {
                request.destroy();
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
    const channel = getOutputChannel();
    channel.appendLine(`Starting LensNN server: ${pythonPath} ${args.join(' ')}`);
    channel.show(true);
    // No cwd override: runsDirectory is passed to the CLI as its own
    // argument (already resolved to an absolute path by the caller when a
    // workspace is open), so the child's working directory doesn't need to
    // match it — and forcing cwd to runsDirectory is actively wrong on a
    // first run, before that folder has ever been created.
    const proc = (0, child_process_1.spawn)(pythonPath, args, {
        env: process.env,
        stdio: ['ignore', 'pipe', 'pipe'],
    });
    serverProcess = proc;
    proc.stdout?.on('data', (chunk) => {
        channel.appendLine(chunk.toString().trim());
    });
    proc.stderr?.on('data', (chunk) => {
        channel.appendLine(chunk.toString().trim());
    });
    proc.on('exit', (code, signal) => {
        channel.appendLine(`LensNN server exited (${code ?? 'unknown'}, ${signal ?? 'no signal'})`);
        if (serverProcess === proc) {
            serverProcess = null;
        }
    });
    // A ChildProcess is an EventEmitter; an 'error' event with no listener
    // throws in Node and can crash the extension host. This also gives us
    // the real failure reason (e.g. "python: command not found") instead
    // of just a generic health-check timeout.
    let spawnError = null;
    proc.on('error', (err) => {
        spawnError = err;
        channel.appendLine(`Failed to start LensNN server: ${err.message}`);
    });
    try {
        await Promise.race([
            waitForHealthCheck(`http://127.0.0.1:${port}/health`),
            new Promise((_resolve, reject) => {
                proc.once('error', reject);
                proc.once('exit', (code) => {
                    if (code !== 0) {
                        reject(new Error(`LensNN server exited early (code ${code ?? 'unknown'})`));
                    }
                });
            }),
        ]);
    }
    catch (error) {
        stopLensnnServer();
        throw spawnError ?? error;
    }
    return { port, runsDirectory };
}
function stopLensnnServer() {
    if (serverProcess) {
        const channel = getOutputChannel();
        channel.appendLine('Stopping LensNN server');
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