# EA Atlas for Claude

**The easiest way to use EA Atlas.** If you do not have a licence for Microsoft Copilot Studio or GitHub Copilot, use Claude. There is nothing to install, no IT set-up and no coding: it works in your web browser, the Claude desktop app or on your phone.

## What you need

- A Claude account. Any plan works, including the free one. Free plans have tighter usage limits, so building a large atlas in one go may need a paid plan.
- The file `enterprise-architecture-atlas-claude.zip` from this page. **Do not unzip it.**

## Set it up (about 5 minutes, once)

1. **Download the zip file** and keep it somewhere you can find it, for example your Downloads folder.
2. **Let Claude create files.** In Claude, open **Settings**, then **Capabilities**, and switch on **Code execution and file creation** (on newer screens it is called **Create and edit files**).
    - On a Team or Enterprise plan, an owner of your Claude organisation may need to switch this on, and Skills, for everyone. Ask whoever manages Claude at your company.
3. **Add the skill.** Go to **Customize**, then **Skills**. Select the **+** button, choose **Create skill**, then **Upload a skill**, and pick the zip file.
4. **Check it is on.** EA Atlas now appears in your list of skills. Make sure its switch is on.

## Try it

Start a new chat and type:

> Show me the ArchiSurance example atlas.

After a minute or two you get the dashboard and the Excel file for a fictional insurer. Open the dashboard and click around.

## Build your own

In a new chat, say who you are mapping, for example:

> Build an EA atlas for Contoso Insurance, insurance pack.

Claude suggests a plan and waits for you to agree. If you have files (an application list, a supplier register, an org chart, invoices, an Archi model), attach them. If you have nothing, Claude can start from public sources such as the annual report and press releases.

## Keep it up to date

Whenever something changes, tell Claude in plain words and attach any new files:

> We have retired the old CRM and signed a new contract with Acme for payments. The contract is attached.

Claude shows you what it will change, then builds a new version and tells you what changed.

## Claude Code (for developers)

If you use Claude Code, add this repository as a plugin marketplace and install the plugin:

```bash
claude plugin marketplace add apisteme/ea-atlas
claude plugin install enterprise-architecture-atlas@ea-atlas
```

The atlas is written to an `ea-atlas/` folder in your project, so you can keep it in Git.

## If something goes wrong

- **The upload is refused.** Check that you uploaded the zip file itself, not an unzipped folder, and that Skills are allowed on your plan.
- **Claude answers but no files appear.** Code execution is probably off. Switch it on (step 2) and start a new chat.
- **Anything else.** Use the **Feedback** button at the top of this page to tell us.
