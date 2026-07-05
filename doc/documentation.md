# Documentation

LifePilot docs live under `doc/`.

## Contents


| Path                                 | Description                                                                          |
| ------------------------------------ | ------------------------------------------------------------------------------------ |
| [documentation.md](documentation.md) | Documentation index: folder layout, diagram workflow, and viewing diagrams in Cursor |
| [concept/](concept/)                 | Product concept: planned features, solution structure, UI prototype and diagrams     |
| [data/](data/)                       | Sample and reference data — shopping categories and items ([data model](data/README.md)) |


## Diagrams

Mermaid sources are `*.mmd` files under `doc/`. Markdown pages embed the rendered **PNG** next to each `.mmd`.

### Update diagram flow

1. Edit the `.mmd` file.
2. From the repository root, run this command to update the PNG:

```powershell
.\scripts\render-diagrams.ps1
```

Requires [Node.js](https://nodejs.org/) (`npx`). Commit updated `.png` files after changing any `.mmd` source.

### Viewing diagrams in Cursor

Cursor’s rich **Preview** tab (the **Preview** pill on the Markdown tab) often **does not load local PNG files** — only the image alt text is shown. The PNG may still be present; check the path in the repo or open the file directly.

**What works**

- **Text Editor** for the `.md` file, then **Markdown: Open Preview** (`Ctrl+Shift+V`) on that editor tab
- View on **GitHub** after the PNG is committed

