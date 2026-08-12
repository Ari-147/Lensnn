import * as http from 'http';
import * as net from 'net';
import { ChildProcess, spawn } from 'child_process';
import * as vscode from 'vscode';
import { resolvePythonPath } from './pythonResolver';

let serverProcess: ChildProcess | null = null;
let outputChannel: vscode.OutputChannel | null = null;

function getOutputChannel(): vscode.OutputChannel {
  if (!outputChannel) {
    outputChannel = vscode.window.createOutputChannel('LensNN Server');
  }
  return outputChannel;
}

function parsePortRange(portRange: string): [number, number] {
  const parts = portRange.split('-').map((part) => parseInt(part, 10));
  if (parts.length !== 2 || parts.some((value) => Number.isNaN(value))) {
    throw new Error(`Invalid portRange: ${portRange}`);
  }
  return [parts[0], parts[1]];
}

async function isPortFree(port: number): Promise<boolean> {
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

export async function findFreePort(portRange: string): Promise<number> {
  const [start, end] = parsePortRange(portRange);
  for (let port = start; port <= end; port += 1) {
    if (await isPortFree(port)) {
      return port;
    }
  }
  throw new Error(`No free port found in range ${portRange}`);
}

function waitForHealthCheck(url: string, timeoutMs = 10000): Promise<void> {
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
        } else if (Date.now() - start > timeoutMs) {
          reject(new Error('Health check timed out'));
        } else {
          setTimeout(attempt, 200);
        }
      });

      request.on('timeout', () => {
        request.destroy();
      });

      request.on('error', () => {
        if (Date.now() - start > timeoutMs) {
          reject(new Error('Health check timed out'));
        } else {
          setTimeout(attempt, 200);
        }
      });
    };

    attempt();
  });
}

export async function startLensnnServer(
  configuredPythonPath: string,
  workspaceFolder: string | undefined,
  runsDirectory: string,
  portRange: string,
): Promise<{ port: number; runsDirectory: string }> {
  if (serverProcess) {
    stopLensnnServer();
  }

  const channel = getOutputChannel();
  const pythonPath = await resolvePythonPath(configuredPythonPath, workspaceFolder, (line) =>
    channel.appendLine(line),
  );

  const port = await findFreePort(portRange);
  const args = ['-m', 'lensnn', 'serve', runsDirectory, '--port', port.toString()];

  channel.appendLine(`Starting LensNN server: ${pythonPath} ${args.join(' ')}`);
  channel.show(true);

  // No cwd override: runsDirectory is passed to the CLI as its own
  // argument (already resolved to an absolute path by the caller when a
  // workspace is open), so the child's working directory doesn't need to
  // match it — and forcing cwd to runsDirectory is actively wrong on a
  // first run, before that folder has ever been created.
  const proc = spawn(pythonPath, args, {
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
  let spawnError: Error | null = null;
  proc.on('error', (err) => {
    spawnError = err;
    channel.appendLine(`Failed to start LensNN server: ${err.message}`);
  });

  try {
    await Promise.race([
      waitForHealthCheck(`http://127.0.0.1:${port}/health`),
      new Promise<void>((_resolve, reject) => {
        proc.once('error', reject);
        proc.once('exit', (code) => {
          if (code !== 0) {
            reject(new Error(`LensNN server exited early (code ${code ?? 'unknown'})`));
          }
        });
      }),
    ]);
  } catch (error) {
    stopLensnnServer();
    throw spawnError ?? error;
  }

  return { port, runsDirectory };
}

export function stopLensnnServer(): void {
  if (serverProcess) {
    const channel = getOutputChannel();
    channel.appendLine('Stopping LensNN server');
    try {
      serverProcess.kill();
    } catch {
      // ignore
    }
    serverProcess = null;
  }
}
