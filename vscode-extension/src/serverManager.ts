import * as http from 'http';
import * as net from 'net';
import * as path from 'path';
import { ChildProcess, spawn } from 'child_process';
import * as vscode from 'vscode';

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
      const request = http.get(url, (response) => {
        response.resume();
        if (response.statusCode === 200) {
          resolve();
        } else if (Date.now() - start > timeoutMs) {
          reject(new Error('Health check timed out'));
        } else {
          setTimeout(attempt, 200);
        }
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
  pythonPath: string,
  runsDirectory: string,
  portRange: string,
): Promise<{ port: number; runsDirectory: string }> {
  if (serverProcess) {
    stopLensnnServer();
  }

  const port = await findFreePort(portRange);
  const args = ['-m', 'lensnn', 'serve', runsDirectory, '--port', port.toString()];

  const outputChannel = getOutputChannel();
  outputChannel.appendLine(`Starting LensNN server: ${pythonPath} ${args.join(' ')}`);
  outputChannel.show(true);

  serverProcess = spawn(pythonPath, args, {
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
  } catch (error) {
    stopLensnnServer();
    throw error;
  }

  return { port, runsDirectory };
}

export function stopLensnnServer(): void {
  if (serverProcess) {
    const outputChannel = getOutputChannel();
    outputChannel.appendLine('Stopping LensNN server');
    try {
      serverProcess.kill();
    } catch {
      // ignore
    }
    serverProcess = null;
  }
}
