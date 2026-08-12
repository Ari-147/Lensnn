import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';

const VENV_DIR_CANDIDATES = ['.venv', 'venv', path.join('python', '.venv'), path.join('python', 'venv')];

function venvPythonPath(venvDir: string): string {
  return process.platform === 'win32'
    ? path.join(venvDir, 'Scripts', 'python.exe')
    : path.join(venvDir, 'bin', 'python');
}

function detectWorkspaceVenv(workspaceFolder: string | undefined): string | undefined {
  if (!workspaceFolder) {
    return undefined;
  }
  for (const candidate of VENV_DIR_CANDIDATES) {
    const candidatePath = venvPythonPath(path.join(workspaceFolder, candidate));
    if (fs.existsSync(candidatePath)) {
      return candidatePath;
    }
  }
  return undefined;
}

async function detectPythonExtensionInterpreter(
  workspaceFolder: string | undefined,
): Promise<string | undefined> {
  try {
    const pythonExtension = vscode.extensions.getExtension('ms-python.python');
    if (!pythonExtension) {
      return undefined;
    }
    const api = pythonExtension.isActive ? pythonExtension.exports : await pythonExtension.activate();
    const uri = workspaceFolder ? vscode.Uri.file(workspaceFolder) : undefined;
    const environment = await api?.environments?.getActiveEnvironmentPath?.(uri);
    const candidatePath = environment?.path;
    if (candidatePath && fs.existsSync(candidatePath)) {
      return candidatePath;
    }
  } catch {
    // ms-python.python isn't installed, isn't activatable, or its API
    // shape changed — any of these just means we fall through to PATH.
  }
  return undefined;
}

/**
 * Resolves the Python executable to launch the LensNN server with.
 *
 * Priority: an explicit lensnn.pythonPath setting always wins. Otherwise,
 * auto-detect in order: a workspace virtualenv at a conventional location,
 * then the interpreter currently selected in the Python extension (if
 * installed), then a bare "python"/"python3" left to PATH resolution.
 * This means a fresh clone of a project with a `.venv` "just works"
 * without the user having to hunt down and paste an interpreter path.
 */
export async function resolvePythonPath(
  configuredPath: string,
  workspaceFolder: string | undefined,
  log: (line: string) => void,
): Promise<string> {
  const trimmed = configuredPath.trim();
  if (trimmed.length > 0) {
    log(`Using configured lensnn.pythonPath: ${trimmed}`);
    return trimmed;
  }

  const venv = detectWorkspaceVenv(workspaceFolder);
  if (venv) {
    log(`Auto-detected workspace virtualenv: ${venv}`);
    return venv;
  }

  const fromPythonExtension = await detectPythonExtensionInterpreter(workspaceFolder);
  if (fromPythonExtension) {
    log(`Using interpreter selected in the Python extension: ${fromPythonExtension}`);
    return fromPythonExtension;
  }

  const fallback = process.platform === 'win32' ? 'python' : 'python3';
  log(`No virtualenv or Python extension interpreter found — falling back to "${fallback}" on PATH.`);
  return fallback;
}
