# Enterprise Architecture Atlas

A do-it-yourself enterprise architecture tool for practitioners who cannot justify a commercial EA platform. Claude builds and maintains one model of your organisation and turns it into:

- an **Excel repository**: one tab per element and relationship, with formulas, ready to import into EA tools
- a **clickable dashboard**: capability map with lenses, journeys and swimlane process maps, RACI, application portfolio (TIME), landscape and integration maps, resilience, suppliers, contracts and licences, third-party risk, strategy alignment, regulatory readiness, change impact, what-if scenarios, an optional programme view (merger, acquisition, transformation), traceability and a versioned change log

Every refresh records what changed, field by field, against the previous release.

**Website and live example:** https://apisteme.github.io/ea-atlas/ (the ArchiSurance example dashboard opens in your browser).

## Industry packs

The engine knows nothing about any industry. Packs supply the capability model, typical roles, journeys and processes, a regulation library, a glossary and the labels the dashboard uses (what "critical" means, what the third-party terms are called).

| Pack | Capability reference | Regulation library |
|---|---|---|
| `core` | APQC PCF categories (cross-industry) | NIS2, GDPR, EU AI Act |
| `banking` | BIAN service domains | DORA, EU PSR, EU AI Act |
| `insurance` | ACORD-style insurance domains | DORA, Solvency II review, EU AI Act |

New packs are welcome: see `reference/pack-authoring.md` and validate with `engine/pack_tools.py validate`.

## Bring your Archi model

If you already model in Archi, export nothing: point the importer at your `.archimate` file (or an Open Group exchange `.xml`). It drafts applications, platforms and what runs on them, roles, interfaces, journeys from triggering chains, data objects, goals and principles, and keeps an ID map so later imports refresh instead of duplicating.

## Install

Ready-made downloads are on the [website](https://apisteme.github.io/ea-atlas/#kits) and in [`docs/downloads/`](docs/downloads/).

| Assistant | Kit | Guide |
|---|---|---|
| Claude (apps and Claude Code) | `enterprise-architecture-atlas-claude.zip`, or this repository as a plugin marketplace | [kits/claude](kits/claude/README.md) |
| Microsoft Copilot Studio | `enterprise-architecture-atlas-copilot-studio.zip` | [kits/copilot-studio](kits/copilot-studio/README.md) |
| GitHub Copilot (VS Code, CLI) | `enterprise-architecture-atlas-github-copilot.zip` | [kits/github-copilot](kits/github-copilot/README.md) |

Claude Code:

```bash
claude plugin marketplace add apisteme/ea-atlas
claude plugin install enterprise-architecture-atlas@ea-atlas
```

Requirements for the build: Python 3 (standard library only). Used when present: Node.js (otherwise the identical Python engine), openpyxl (otherwise a built-in Excel writer with plain formatting), LibreOffice (Excel recalculation), jsdom (dashboard smoke test).

To carry an atlas between machines or assistants, `engine/atlas_bundle.py pack` writes it to one file and `unpack` restores it.

## Quick start without an assistant

```bash
cd plugins/enterprise-architecture-atlas/skills/enterprise-architecture-atlas
cp -r samples/archisurance /tmp/atlas
python3 engine/build.py --workspace /tmp/atlas
open /tmp/atlas/output/ArchiSurance_EA_Dashboard.html
```

Start your own: `python3 engine/pack_tools.py new-workspace --pack insurance --name "My Insurer" --short MyIns --out ea-atlas`, then fill `ea-atlas/model/` (field reference in `reference/model-schema.md`).

## Layout

```
.claude-plugin/marketplace.json      Claude Code marketplace
plugins/enterprise-architecture-atlas/
  skills/enterprise-architecture-atlas/
    SKILL.md        instructions Claude follows (build, refresh, analyse, pack modes)
    engine/         Python and JavaScript build, dashboard template, what-if and change impact engines, tests
    importers/      ArchiMate importer
    packs/          core, banking, insurance
    samples/        ArchiSurance example model
    reference/      model schema, outputs and behaviour, pack authoring
kits/               Claude, Copilot Studio and GitHub Copilot instructions and setup guides
tools/              make_copilot_skill.py, make_github_copilot_kit.py, build_site.py
site/               website stylesheet and the list of examples
docs/               the built website (GitHub Pages), with the downloads and example outputs
```

## Updating the website and downloads

```bash
pip install markdown playwright   # playwright only for screenshots; Chromium must be installed
python3 tools/build_site.py
```

This rebuilds every kit, every example listed in `site/examples.json`, the screenshots and the pages into `docs/`. To add an example, put its model under `samples/<name>/model/`, add an entry to `site/examples.json` and rebuild.

## Data and honesty

Every application and supplier carries a confidence tag: Customer-provided, Public, Partly confirmed or Illustrative. Figures the model does not supply (costs, contract terms, SLAs, recovery targets) are generated and tagged Illustrative until replaced. The dashboard shows the tag everywhere.

## Licence

MIT. See `NOTICE.md` for the ArchiSurance sample model, industry standards and regulation summaries.
