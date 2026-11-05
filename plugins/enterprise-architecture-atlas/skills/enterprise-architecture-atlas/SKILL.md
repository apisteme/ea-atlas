---
name: enterprise-architecture-atlas
description: "Build or refresh an enterprise architecture atlas (Excel repository plus clickable dashboard) for any organisation and industry, linking strategy, capabilities, value streams, processes, roles, applications, suppliers, risk and regulation, with change impact and what-if analysis. Uses industry packs (banking, insurance, cross-industry) and can import ArchiMate models from Archi."
---

# Enterprise Architecture Atlas

An atlas is one master model per organisation that produces two outputs: an Excel repository and a clickable HTML dashboard. Information arrives through an inbox, links, an ArchiMate import or conversation; each refresh updates the model, records what changed, and rebuilds both outputs.

Nothing in the engine is specific to an industry. Industry knowledge lives in packs (`packs/`); organisation knowledge lives in the workspace model (`ea-atlas/model/*.json`).

## When to use

- "Build an EA atlas, capability map or application portfolio dashboard for <organisation>"
- "Import our Archi model", "here is our .archimate file"
- "Refresh the atlas", "I have dropped new files in the inbox", "update from this link"
- Updates to applications, suppliers, contracts, licences, roles and RACI, processes, interfaces, resilience, strategy, regulation, scenarios, the change backlog or a programme
- "What is the impact of <event or change>?", "what if this system or supplier fails?", "model this feature or epic"
- "How ready are we for <regulation>?"
- "Add an industry pack for <industry>"

## Modes

Say which mode you are running.

1. **Build**: no atlas exists. Choose the pack, plan, confirm, gather, build.
2. **Refresh**: an atlas exists. Read the inputs, draft a change set, apply, release.
3. **Analyse**: answer a question or model a scenario without changing the model (unless asked).
4. **Pack**: create or extend an industry pack (see `reference/pack-authoring.md`).

## Writing rules (replies, dashboard, Excel)

- Plain professional British English, as a senior architect would write.
- No em dashes or en dashes anywhere. Use commas, colons, full stops or "to". The build checks outputs.
- Avoid machine-sounding words: leverage, seamless, robust, unlock, game-changing, delve, holistic.
- Short, direct sentences. Name things the way the organisation does.
- Never draw or recreate an organisation's logo. Keep the published dashboard text-only.

## What is where

```
skills/enterprise-architecture-atlas/
  SKILL.md                    this file
  engine/                     build.py (runs everything), build_data.py, build_xlsx.py (+ mini_xlsx.py when openpyxl
                              is missing), build_dashboard.py, scenario_engine.js and feature_engine.js (dashboard and
                              Node) with impact_engine.py (identical Python port), dashboard template and UI modules,
                              diff_snapshots.py, taxonomy.py, pack_tools.py, atlas_bundle.py (whole atlas as one file),
                              check_env.py, smoke_test.js, test_engine_parity.py
  importers/archimate_import.py   Archi .archimate or Open Group exchange .xml -> draft model
  packs/core|banking|insurance    profile, capabilities L1 to L3, roles, journeys, processes, regulations, glossary
  samples/archisurance/       example model built from Archi's ArchiSurance sample (insurance pack)
  reference/                  model-schema.md, outputs.md, pack-authoring.md
```

The workspace for one organisation (created by `pack_tools.py new-workspace`):

```
ea-atlas/
  model/            organisation.json and one JSON file per element type (the source of truth; see reference/model-schema.md)
  model/_import/    ArchiMate import: normalised model, ID map, drafts
  inbox/<type>/     drop new information here, any format: applications, procurement, licences, roles_raci,
                    processes, capabilities, interfaces, resilience, strategy, regulation, scenarios,
                    change_backlog, archimate
  sources/links.md  public and internal links to read
  repository/       data.json, versions/, engine results, atlas_page.html (generated; do not edit)
  output/           Excel, standalone dashboard, prompt file; output/archive/v<version>/ per release
  processed/        inbox files move here after a refresh
  changelog.md      release notes, newest first
```

## Industry packs

| Pack | Capability reference | Criticality concept | Third-party concept |
|---|---|---|---|
| `core` | APQC PCF categories | Business-critical service | Critical supplier |
| `banking` | BIAN service domains | Critical or important function (DORA) | Material outsourcing, DORA Art. 30 |
| `insurance` | ACORD-style domains | Critical or important function (DORA, Solvency II) | Critical outsourcing, DORA Art. 30 |

Pick the closest pack. If none fits, use `core` and offer to write a pack for the industry (Pack mode). Labels, layers, interface families and terms come from the pack profile and can be overridden per organisation in `organisation.json` → `profile`. Run `python3 engine/pack_tools.py list` to see what is installed.

## Data confidence

Every application and supplier carries one tag, shown everywhere:

| Tag | Meaning | Precedence |
|---|---|---|
| Customer-provided | Confirmed by the user or a file they supplied | 1 (highest) |
| Public | Confirmed by a cited public source | 2 |
| Partly confirmed | Capability confirmed, product or vendor assumed, or "to confirm" | 3 |
| Illustrative | Reference-model placeholder | 4 |

The tag is derived from the `source` text (see the model schema). A higher-precedence value is never overwritten by a lower one. Costs, dates, SLAs, utilisation and assessments stay illustrative until supplied; the engine seeds them and tags them Illustrative.

## Build mode

1. **Choose the pack and plan.** Ask the industry if it is not obvious. Show the pack's metamodel and labels, the scope (segments, process depth, real or illustrative vendors), the outputs, and whether there is a programme (merger, acquisition, transformation). Wait for confirmation.
2. **Create the workspace**: `python3 engine/pack_tools.py new-workspace --pack <pack> --name "<name>" --short <short> --out ea-atlas`. This seeds capabilities, L3s, roles, journeys, processes and the regulation library from the pack.
3. **Gather the organisation's facts**, best source first:
   - Files the user provides (inventory, supplier register, org chart): tag Customer-provided.
   - An ArchiMate model: `python3 importers/archimate_import.py <file> --workspace ea-atlas --source Customer-provided`. Review the drafts in `model/_import/draft/` and carry applications, platforms, roles, interfaces, journeys (triggering chains), data objects, goals and principles into the model files. Keep the `archimate_id` on each item so a later import refreshes rather than duplicates.
   - Public sources: annual report, results presentation (value streams, strategy), regulator, vendor and partner announcements. Record each fact with its link. Check anything current rather than relying on memory.
4. **Write the model files** (`reference/model-schema.md`): organisation (data centres, hosting classes with provider suppliers, owners by category, currency, cost scale), applications, suppliers, interfaces, data domains; map L3 capabilities and journey steps to applications; map regulatory requirements to applications and processes; strategy; example scenarios; an example change backlog (10 to 15 epics, about 40 features for a large estate, fewer for a small one); the programme if there is one. Adapt the pack templates to the organisation: rename, remove and add. Roles must cover technology, data and security as well as the business.
5. **Build**: `python3 engine/build.py --workspace ea-atlas --recalc <xlsx skill>/recalc.py`. Fix every validation error in the model and rebuild. Only the Python standard library is required; Node, openpyxl and LibreOffice are used when present (`engine/check_env.py` reports what the host has).
6. **Calibrate** `change_thresholds` so change impact levels spread across the backlog.
7. **Validate** (below), publish `repository/atlas_page.html` with label `v1.0`, and deliver.

## Refresh mode

1. **Inventory the inputs**: every file in `inbox/`, every link, any new ArchiMate export. Read each one fully (file-reading or pdf-reading skill for non-text files). Note anything unreadable.
2. **Classify** each item by update type (the How to update view lists them) and extract records.
3. **Match** to existing elements: by ID, then exact name, then product or vendor name, then `archimate_id`. List uncertain matches as questions; do not guess.
4. **Draft a change set** grouped by element type: added, updated (old to new), retired, conflicts, questions. For more than 10 changes, or any deletion, show it and ask for confirmation. Apply small, unambiguous updates directly and report them.
5. **Apply** to the model files, respecting confidence precedence. New elements take the next free ID.
6. **Release** (Versioning): raise the version and add the history entry in `model/versioning.json`, then run `engine/build.py`. The build re-derives everything, snapshots the release and diffs it against the previous one.
7. **Publish** to the same dashboard URL with label `v<version>`; copy outputs to `output/archive/v<version>/`; move processed inbox files to `processed/` with a date prefix.
8. **Log** the release in `changelog.md` and **report**: what changed, what it revealed, open questions. Keep it short.

## Moving an atlas between hosts

`python3 engine/atlas_bundle.py pack --workspace ea-atlas` writes the whole atlas (model, change history, latest release snapshot) to one file, `<Org>_atlas_model.json`; `unpack` restores it into an empty workspace. Use it when the workspace will not persist, or to hand the atlas to a colleague or another assistant. A Microsoft Copilot (Copilot Studio, Agent Builder) version of this skill is built with `tools/make_copilot_skill.py` and works from that file.

## Analyse mode

Use the engines rather than reasoning from memory: run `scenario_engine.js` or `feature_engine.js` against `repository/data.json` with node, or build the scenario or feature in the dashboard. Report the impact level, what goes down, degrades or changes, journeys and roles affected, critical functions, recovery time, cost effect and the checks raised. Say which inputs are illustrative.

## Versioning

Every change to the model or the dashboard is a release. No silent edits.

- `model/versioning.json` holds `version`, `release_date` and `history`. Each history entry has version, date, title, one-sentence summary, source (Customer-provided, Public, EA analysis, Platform) and changes (type, action: Added, Updated, Corrected, Removed, Feature, Fix; ids; a short sentence).
- Content changes raise the minor number (1.4 to 1.5); a metamodel restructure raises the major number (2.0). Fixes that change no data still get a minor release.
- Raise the version before the first build of a release. Building first overwrites the previous release's snapshot and the release then shows no changes; if that happens, restore the snapshot from `output/archive/` before rebuilding.
- The diff normalises empty values, so a new optional field does not report every record as changed. Check the detected changes match the intended change set and explain anything unexpected (for example seeded illustrative figures shifting when applications are added).

## Validation (every build, fix before delivery)

- `build.py` reports zero validation errors: every reference resolves (applications, capabilities, roles, processes, suppliers, journeys, requirements, initiatives, programme decisions, features).
- Every L2 capability has an application or is listed as a gap; every L3 maps to applications or is a gap.
- Every application has a supplier, a licence record and a support record, and belongs to at least one process.
- Every step has exactly one Accountable role.
- Excel recalculation reports zero formula errors.
- After changing either impact engine: `python3 engine/test_engine_parity.py --workspace ea-atlas` reports zero differences.
- `node engine/smoke_test.js output/<prefix>_EA_Dashboard.html` (needs jsdom) passes: every view, drawer, lens, the What if? builder for every type, the change builder and every Model what if option, with no console errors.
- One rendered screenshot of any view that changed, checked once.
- Zero em and en dashes in every output.
- Version raised, history entry present, badge and Excel README match `meta.version`, snapshot saved.
- For a new or changed pack: `python3 engine/pack_tools.py validate <pack>`.

## Outputs

See `reference/outputs.md` for the dashboard views and behaviour, the What if? and change impact engines, regulatory readiness, the Excel repository, the optional Copilot kit and the prompt file.

## Delivery

Republish the dashboard to the same URL with label `v<version>`, send the standalone HTML, the Excel and the prompt file, and reply with the version, what changed, two or three findings, and open questions. Cite public sources as links. Keep confidential inputs out of anything public and never publish content the user marked sensitive.

## Example

`samples/archisurance/` is a complete model built from the ArchiSurance sample that ships with Archi (MIT licence), mapped to the insurance pack, with a back-office consolidation programme. Build it with `python3 engine/build.py --workspace <copy of samples/archisurance>` to see every view. Items from the Archi model are tagged Public; everything else is illustrative.
