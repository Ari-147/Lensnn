# LensNN VS Code Extension

Embeds the LensNN local viewer dashboard in a VS Code editor panel.

## Local development

1. Open the `vscode-extension` folder in VS Code.
2. Run `npm install` to install the extension dev dependencies.
3. Press `F5` to launch the Extension Development Host.
4. Open the command palette and run `LensNN: Open Dashboard`.
5. Confirm the placeholder message appears.

## Extension settings

The extension contributes these settings under the LensNN section:

- `lensnn.pythonPath` - default: `python`
- `lensnn.runsDirectory` - default: `./runs`
- `lensnn.portRange` - default: `8700-8799`
