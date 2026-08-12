# LensNN VS Code Extension

Embeds the LensNN local viewer dashboard in a VS Code editor panel.

## Local development

1. Open the `vscode-extension` folder itself in VS Code (not the repository
   root) — the debug configuration in `.vscode/launch.json` is only
   discovered when this folder is the opened workspace root.
2. Run `npm install` in the `vscode-extension` folder if needed.
3. Open the Run and Debug view and select `Run LensNN Extension`.
4. Press `F5` to launch the Extension Development Host.
5. In the Extension Development Host, open the command palette and run `LensNN: Open Dashboard`.
6. Confirm the LensNN dashboard loads in the webview.

## Packaging

1. From the `vscode-extension` folder, run `npm install` if needed, then `npm run package`.
2. The packaged file is `lensnn-0.1.0.vsix` by default.
3. Install locally in a regular VS Code window with:

   `code --install-extension lensnn-0.1.0.vsix`

4. Open the command palette and run `LensNN: Open Dashboard`.

## Extension settings

The extension contributes these settings under the LensNN section:

- `lensnn.pythonPath` - default: `python`
- `lensnn.runsDirectory` - default: `./runs`
- `lensnn.portRange` - default: `8700-8799`
