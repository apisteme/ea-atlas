# EA Atlas for GitHub Copilot

For architects who already use Visual Studio Code and GitHub Copilot. Copilot builds the atlas on your own computer, and the atlas lives in a Git repository, so every change is recorded and can be reviewed like code.

## What you need

- **Visual Studio Code** with **GitHub Copilot** (a paid Copilot plan, or one provided by your organisation). Keep VS Code and the Copilot Chat extension up to date: skills need a recent version.
- **Python 3** on your computer. To check, open a terminal and type `python3 --version` (on Windows: `py --version`). If it is missing, install it from [python.org](https://www.python.org/downloads/); on Windows, tick **Add Python to PATH** during installation.
- **A Git repository** to hold the atlas. Use a **private** repository if the atlas will contain anything confidential.
- The file `enterprise-architecture-atlas-github-copilot.zip` from this page.

## Set it up (about 10 minutes, once)

1. **Download the zip file.**
2. **Unzip it into the top folder of your repository**, the folder that contains the hidden `.git` folder. You should now see a `.github` folder there containing `skills`, `prompts` and `instructions`, plus a file called `EA-ATLAS.md`. If you already had a `.github` folder, the new files are added to it and nothing of yours is replaced.
3. **Open the repository in VS Code.**
4. **Open Copilot Chat** and switch the mode to **Agent**.
5. **Try the example.** Type `/atlas-example` and press Enter. When Copilot asks to run commands in the terminal, allow them: the scripts only read and write inside your repository and never use the internet.
6. **Open the result.** Open `ea-atlas-example/output/ArchiSurance_EA_Dashboard.html` in your web browser.

## Everyday use

Type `/` in Copilot Chat to see the ready-made prompts:

| Type | What it does |
|---|---|
| `/atlas-example` | Builds the ArchiSurance example so you can see every view |
| `/atlas-build` | Starts an atlas for your organisation. Copilot suggests a plan and waits for you to agree |
| `/atlas-refresh` | Reads new files you put in `ea-atlas/inbox/`, shows the changes, and builds a new version |
| `/atlas-what-if` | Answers "what happens if..." questions without changing anything |

You can also just ask in your own words, for example "Import our Archi model from the inbox and build the atlas".

After each new version, **commit** the changes with the version number in the message. Git then holds the full history of your atlas.

## What you get

- `ea-atlas/output/<Organisation>_EA_Dashboard.html`: the dashboard. Open it in any browser; it works offline.
- `ea-atlas/output/<Organisation>_EA_Repository.xlsx`: the Excel repository.
- `ea-atlas/model/`: the atlas itself, one file per kind of element. This is what you review and commit.
- `ea-atlas/changelog.md`: what changed in each version.

To share the dashboard, send the file, or publish the `ea-atlas/output/` folder on an internal website.

## If something goes wrong

- **The `/atlas-...` prompts do not appear.** Check that the `.github` folder is at the top of the repository you opened, then update VS Code and the Copilot Chat extension.
- **"python3 is not recognised" (Windows).** Install Python from python.org with **Add Python to PATH** ticked, then restart VS Code.
- **Anything else.** Use the **Feedback** button at the top of this page to tell us.

## Without Copilot

Everything also runs by hand from a terminal:

```bash
cp -r .github/skills/enterprise-architecture-atlas/samples/archisurance ea-atlas-example
python3 .github/skills/enterprise-architecture-atlas/engine/build.py --workspace ea-atlas-example
```
