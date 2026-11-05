# EA Atlas for Microsoft Copilot Studio

For organisations that use Microsoft 365. You create an "agent" in Copilot Studio, give it the EA Atlas skill, and then anyone you share it with can use it in Teams or Microsoft 365 Copilot.

## What you need

- A Microsoft 365 work account with access to **Copilot Studio** (a licence or a trial) and permission to create agents. If you are not sure, ask your IT team.
- The file `enterprise-architecture-atlas-copilot-studio.zip` from this page. **Do not unzip it.**

Skills in Copilot Studio are new (in preview), so screens may look slightly different from these steps.

## Set it up (about 15 minutes, once)

1. **Download the zip file.**
2. **Create an agent.** Open [Copilot Studio](https://copilotstudio.microsoft.com), create a new agent and call it, for example, "EA Atlas".
3. **Give it short instructions.** Paste this into the agent's instructions:

    > You help enterprise architects build and maintain an EA atlas. For any request about an EA atlas, capability map, application portfolio, change impact, what-if or regulatory readiness, use the enterprise-architecture-atlas skill. Ask the user to attach their atlas file when they have one.

4. **Add the skill.** Go to **Build**, then **Skills**, then **Add skill**, then **Upload a skill**, and choose the zip file.
    - If it is refused, or the skill does not appear in the list, try the other download, `enterprise-architecture-atlas-copilot-studio-folder.zip`.
5. **Optional: let it research.** If you want the agent to look up public information (annual reports, press releases, regulators), switch on web search for the agent.
6. **Test it** in the preview chat by typing:

    > Show me the ArchiSurance example atlas.

   You should get three files, each with a **Download** button: the dashboard, the Excel file and the atlas file.
7. **Publish** the agent to Teams or Microsoft 365 Copilot when the test works.

There is no "code" setting to switch on: the agent runs the skill's scripts by itself.

## Everyday use: keep your atlas file

Copilot does not remember files between conversations. That is why every session ends with an **atlas file** (`<Organisation>_atlas_model.json`) that holds the whole atlas and its history.

1. Save the atlas file somewhere safe, such as OneDrive or SharePoint.
2. Next time, **attach the atlas file first**, then say what has changed and attach any new documents.
3. Save the new atlas file it gives back, replacing the old one.

If you skip this, the next conversation starts from nothing.

## If something goes wrong

- **"Your environment blocks these files".** This package contains no blocked file types, so you probably uploaded an older download. Download it again from this page.
- **The agent describes what it would do but returns no files.** Look at the agent's activity view to see whether it ran `check_env.py` and `build.py`, then tell us what you saw using the **Feedback** button.
- **A file is missing from the answer.** Files over 10 MB are not returned. A normal atlas is well under 1 MB, so tell us if you see this.

## For maintainers: how the package is built and checked

The zip is built from this repository with:

```bash
python3 tools/make_copilot_skill.py
```

This writes `dist/copilot-studio/enterprise-architecture-atlas.zip` (SKILL.md at the top of the zip) and `dist/copilot-studio/enterprise-architecture-atlas-folder.zip` (the same files inside a folder). It checks them against the published Agent Builder skill limits: allowed file types only and no .js, .html or shell files (tenants often block them), folder depth of 3 or less, at most 350 files, under 25 MB a file and 50 MB a zip, instructions under 20,000 characters, name and description within the Agent Skills specification, UTF-8 without a byte-order mark.

The dashboard page, with its JavaScript, is stored as a Python string in `scripts/dashboard_page.py`, because some tenants refuse .js and .html files. Node and openpyxl are optional: the Python engine gives identical results, and without openpyxl the Excel has the same tabs and formulas with plain formatting. Microsoft documents that agents in the new experience create files with Python and return them as file cards for 28 days, up to 10 MB each.
