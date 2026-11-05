# Enterprise Architecture Atlas for Claude

The original version of the skill. Claude writes the model, runs the build in its own workspace and can publish the dashboard as a page with its own link.

## Claude apps (web, desktop, mobile)

1. Turn on code execution: in **Settings** > **Capabilities**, turn on **Code execution and file creation**. On Team and Enterprise plans an owner enables it, and Skills, under **Organization settings**.
2. Download `enterprise-architecture-atlas-claude.zip`.
3. Go to **Customize** > **Skills**, select **+**, then **Create skill** > **Upload a skill**, and upload the zip.
4. Make sure the skill is switched on, then ask: "Show me the ArchiSurance example atlas" or "Build an EA atlas for <organisation>, insurance pack".

Custom skills stay private to you until you share them.

## Claude Code

Add this repository as a plugin marketplace and install the plugin:

```bash
claude plugin marketplace add apisteme/ea-atlas
claude plugin install enterprise-architecture-atlas@ea-atlas
```

Then ask in your project: "Build an EA atlas for <organisation>" or "Import our Archi model from inbox/archimate and build the atlas". The atlas is written to `ea-atlas/` in the project.

## What Claude does that the other kits do not

- Publishes the dashboard as a hosted page and republishes it to the same link on every release, with saved scenarios shared between viewers.
- Reads attachments in any format, for example PDFs, Word files and spreadsheets, and researches public sources itself.
- Recalculates the Excel and runs the dashboard test before delivery when the tools are available.
