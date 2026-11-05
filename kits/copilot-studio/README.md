# Enterprise Architecture Atlas for Microsoft Copilot Studio

The same atlas engine as the Claude skill, packaged as a Copilot Studio skill. Build it with:

```bash
python3 tools/make_copilot_skill.py
```

This writes `dist/copilot-studio/enterprise-architecture-atlas.zip` (SKILL.md at the top of the zip) and `dist/copilot-studio/enterprise-architecture-atlas-folder.zip` (the same files inside a folder), and checks them against the published package limits.

## Set up in Copilot Studio

Skills in the new Copilot Studio agent experience are in preview, so screens and limits can change.

1. Open Copilot Studio and create an agent in the new agent experience, for example "EA Atlas".
2. There is no code execution setting to turn on. In the new agent experience the agent runs Python itself whenever it needs to create a file, and the packages it has include openpyxl, so the Excel keeps its full formatting. (Older classic agents had a separate "code interpreter" switch; it does not apply here.)
3. Give the agent short instructions, for example: "You help enterprise architects build and maintain an EA atlas. For any request about an EA atlas, capability map, application portfolio, change impact, what-if or regulatory readiness, use the enterprise-architecture-atlas skill. Ask the user to attach their atlas file when they have one."
4. Go to **Build** > **Skills** > **Add skill** > **Upload a skill**, and upload `enterprise-architecture-atlas.zip`.
   - If the upload is rejected or the skill does not appear in the list, replace it with `enterprise-architecture-atlas-folder.zip`.
5. If you want the agent to research public sources (annual reports, regulators), enable web search or knowledge sources for the agent. The skill's scripts never use the network.
6. Test in the preview chat, in this order:
   - "Show me the ArchiSurance example atlas." The agent should run the scripts and return three file cards with a **Download** action: the dashboard (.html), the Excel file and the atlas file.
   - "Build an EA atlas for <a fictional company>, insurance pack, with these applications: ..."
   - Attach the atlas file from the previous step and ask: "What happens if the mainframe fails?"
7. Publish the agent to Teams or Microsoft 365 Copilot when the tests pass.

## How users work with it

- The sandbox does not keep files between sessions. Each session ends with three files: the dashboard (open in any browser), the Excel repository and `<Org>_atlas_model.json`, the **atlas file**.
- Users keep the atlas file (OneDrive or SharePoint) and attach it at the start of the next session. It holds the whole model and its change history.
- Saved scenarios and features inside the dashboard stay in the viewer's browser. To keep one permanently, ask the agent to add it to the atlas.

## What to check in your tenant

Microsoft documents that agents in the new experience create files with Python and return them as file cards (in the Preview tab, Teams, Microsoft Copilot and web chat), up to 10 MB per file, kept for 28 days. It does not say whether the agent runs scripts bundled in an uploaded skill, so test these before rolling out:

| Question | Why it matters | If it fails |
|---|---|---|
| Does the agent run the skill's Python scripts? | Everything is built by scripts | Check the agent's activity or reasoning view for the `check_env.py` and `build.py` runs. If it only describes them, tell me what it shows |
| Does it return all three files as file cards? | Users need the dashboard, Excel and atlas file | Files over 10 MB are not returned; the dashboard and atlas file are well under 1 MB for a typical atlas. If an .html card is blocked, tell me the message |
| Is the zip accepted with SKILL.md at the top level? | Microsoft's examples differ | Use the folder zip |
| Is Node available? | Not needed: the Python engine gives identical results | Nothing to do |
| Is openpyxl available? | Microsoft lists it as available; it only affects Excel formatting | Nothing to do: if it is missing, the built-in writer produces the same tabs and formulas |

## Limits the package meets

Checked by `make_copilot_skill.py` against the Agent Builder skill limits (the closest published limits): allowed file types only, and no .js, .html or shell files (tenants often block them), folder depth of 3 or less, 47 files (limit 350), under 1 MB (limit 50 MB per zip, 25 MB per file), instructions about 11,000 characters (limit 20,000), name and description within the Agent Skills specification, UTF-8 without a byte-order mark.
