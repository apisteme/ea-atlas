# Enterprise Architecture Atlas for GitHub Copilot

The atlas skill for GitHub Copilot in VS Code (agent mode) and the Copilot CLI. Copilot reads the skill, writes the model files and runs the build scripts in your terminal. The atlas lives in your own Git repository, so every release is a commit.

## Install

1. Create or open the repository that will hold your atlas. Use a **private** repository if the atlas will hold anything confidential.
2. Download `enterprise-architecture-atlas-github-copilot.zip` and unzip it at the root of the repository. You get:

   ```
   .github/skills/enterprise-architecture-atlas/   the skill (instructions, engine, packs, ArchiSurance sample)
   .github/prompts/atlas-*.prompt.md               ready-made prompts
   .github/instructions/ea-atlas.instructions.md   rules Copilot applies to files under ea-atlas/
   EA-ATLAS.md                                     this guide
   ```

   If you already have a `.github` folder, the files merge into it; nothing of yours is replaced.
3. Make sure Python 3 is installed (`python3 --version`). Nothing else is required. If Node.js or the Python package openpyxl are installed, they are used: Node gives the same results faster, openpyxl gives the Excel its full formatting.
4. Open the repository in VS Code, open Copilot Chat and choose **Agent** mode. Skills need a recent VS Code and Copilot Chat extension.

## Use

Type `/` in the chat to see the prompts:

| Prompt | What it does |
|---|---|
| `/atlas-example` | Builds the ArchiSurance example so you can see every dashboard view |
| `/atlas-build` | Starts a new atlas for your organisation: chooses the industry pack, plans, then builds `ea-atlas/` |
| `/atlas-refresh` | Reads new files in `ea-atlas/inbox/` and links in `ea-atlas/sources/links.md`, shows the change set, releases a new version |
| `/atlas-what-if` | Runs the impact engine on a scenario or change, without changing the model |

You can also ask in your own words, for example "Import our Archi model from inbox/archimate and build the atlas", or type `/enterprise-architecture-atlas`.

Copilot asks before running terminal commands unless you have allowed them. The scripts only read and write inside the repository and never use the network.

## What you get

- `ea-atlas/output/<Org>_EA_Dashboard.html`: the dashboard. Open it in any browser; it works offline.
- `ea-atlas/output/<Org>_EA_Repository.xlsx`: the Excel repository.
- `ea-atlas/model/`: the model, one JSON file per element type. This is what you commit and review in pull requests.
- `ea-atlas/changelog.md` and `output/archive/v<version>/`: release notes and the files of every release.

To share the dashboard, publish `ea-atlas/output/` on an internal site, or with GitHub Pages from a private repository if your plan allows it.

## Without Copilot

Everything also runs by hand:

```bash
cp -r .github/skills/enterprise-architecture-atlas/samples/archisurance ea-atlas-example
python3 .github/skills/enterprise-architecture-atlas/engine/build.py --workspace ea-atlas-example
```
