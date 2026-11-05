# Model files

One folder of JSON files per organisation: `ea-atlas/model/`. The engine reads only these files and the industry pack named in `organisation.json`. Fields not listed here are kept and passed through.

IDs are stable: never renumber, never reuse. New items take the next free ID.

## organisation.json

| Field | Meaning |
|---|---|
| `name`, `short_name` | Full and short name. The short name labels the dashboard, files and messages |
| `file_prefix`, `dashboard_title` | Optional. Output file prefix (default from short name) and dashboard title |
| `pack` | Industry pack: `core`, `banking`, `insurance` or any pack folder |
| `as_of` | Date the model describes (ISO) |
| `seed`, `cost_scale` | Seed for illustrative figures; multiplier for illustrative costs (1.0 suits a mid-size bank, 0.3 a small insurer) |
| `currency` | `{"symbol": "€", "code": "EUR"}` |
| `context` | Short facts shown in the navigation footer |
| `disclaimer` | Banner text about data confidence |
| `sources` | `{key: url}`; any `ref` field may use a key |
| `data_centres` | `[{id, name, role, mode, kind: primary or secondary, source}]` |
| `dc_model` | `active-passive`, `active-active` or `single` |
| `hosting` | `{hosting value: {kind, licence_model, providers: [{supplier, role, except_apps}], no_licence_cost, evergreen}}`. `kind`: `internal` (own data centres), `vendor` (SaaS or cloud), `hybrid`, `third-party` (outsourced, partner, scheme), `end-user`. Providers are added to every application with that hosting |
| `customer_role` | Role ID of the customer (lane on process maps, customer exposure in change impact) |
| `owners_by_category`, `tech_owners_by_category` | Default business and technology owner role by application category |
| `default_business_owner`, `default_tech_owner` | Fallback owners |
| `licence_metric_by_category` | Default licence metric by category |
| `change_thresholds` | Optional `[medium, high, critical]` change impact score thresholds; default `[15, 30, 50]`. Lower them for a small estate so levels spread |
| `profile` | Optional overrides of the pack profile (labels, layers, interface families) |

## capabilities.json and capabilities_l3.json

`capabilities.json`: `[{id, name, parent, description, std_ref, importance, maturity, source}]`. L1 has `parent: ""` (Cnn); L2 has an L1 parent (Cnn.nn). `std_ref` is the reference model mapping (BIAN service domain, insurance domain, APQC category). `maturity` 1 to 5; seeded if blank.

`capabilities_l3.json`: `{L2 id: [{name, description, apps, source, id}]}`. `apps` lists the applications that realise the L3; `null` inherits every application of the L2; `[]` is a gap. IDs default to `<L2>.<nn>` by position, so append new L3s at the end of the list.

## roles.json

`[{id, name, unit, family, source, customer, tech}]`. Family is one of Front office, Middle office, Back office, Operations, Business, Finance, Risk (2nd line), Support, Technology, Leadership, External. `tech: true` marks a technology leader whose unit should group with technology roles.

## suppliers.json

`[{id, name, type, hq, location, tier, risk, material, exit_plan, source, ref, internal, no_contract, contract}]`

- `tier`: Strategic, Important, Tactical, Internal, Statutory. `risk`: Low, Medium, High.
- `material`: true for material outsourcing or critical ICT third parties (label from the pack profile).
- `exit_plan`: Not documented, Documented, Documented, untested, Documented, tested <year>, Not required, N/A.
- `internal: true` for in-house delivery (no contract). `no_contract: true` for regulators and schemes.
- `contract`: optional real terms `{start, end, notice_months, auto_renew, change_of_control_clause, regulatory_terms, annual_value, source}`. Missing terms are seeded and tagged Illustrative.

## applications.json

| Field | Meaning |
|---|---|
| `id`, `name`, `product`, `vendor` | Vendor is the primary supplier ID |
| `category` | Drives integration-map layer, owners and licence metric |
| `capabilities` | L2 capability IDs (L3 mappings add their parent L2 automatically) |
| `lifecycle`, `time` | Production, Migrating, Phase-out; TIME: Tolerate, Invest, Migrate, Eliminate |
| `tier` | 0 to 3 |
| `hosting` | A key of `organisation.hosting`, or free text classified by keyword |
| `critical` | Supports a critical or important function (label from the profile) |
| `source`, `ref` | Confidence comes from `source`: starts with Customer-provided, Public, contains "confirm" (Partly confirmed), else Illustrative |
| `programme_lens` | Text starting with a lens value (for example `Likely converge - ...`) when a programme exists |
| `suppliers` | Extra supplier roles `[{supplier, role}]` such as SI, AMS, Agency, Hosting |
| `runs_on` | `[{app, status}]` platform dependencies |
| `platform` | Marks a platform: `{hosts: [hosting prefixes it hosts], carries: "protocol regex it carries", note: "caveat shown when it fails"}` |
| `customer_facing` | Channel application customers use |
| `business_owner`, `tech_owner`, `users`, `func_fit`, `tech_health` | Optional; defaults from category maps and seeded values |
| `end_of_support`, `licence`, `support`, `resilience`, `data_centres` | Optional real values that replace the illustrative ones |

## value_streams.json

```json
{"customer_value_streams": [{"id": "CVS1", "name": "", "scope": "", "owner": "R..", "source": "", "ref": "", "ref_title": "", "short": "", "cross_cutting": false}],
 "journeys": [{"id": "VS01", "name": "", "parent": "CVS1", "owner": "R..", "trigger": "", "outcome": "", "source": "",
   "steps": [{"name": "", "capabilities": ["C.."], "apps": ["A.."], "R": ["R.."], "A": "R..", "C": [], "I": []}]}]}
```
Step IDs are `<journey>.<n>` by position: append new steps, and mark removed steps retired rather than deleting them when other items reference them. Exactly one Accountable per step.

## processes.json

`[{id, name, category: Operate|Manage|Support, parent, owner, roles, capabilities, apps, journeys, source}]`. L1 groups have no parent (Pn); L2 processes have one (Pn.n).

## data_domains.json, interfaces.json

`data_domains`: `[{id, name, sor, consumers, steward, source}]`.
`interfaces`: `[{id, source_app, target_app, data, protocol, frequency, source}]`. The protocol text is classified into the families in the profile (events, messaging, API, file, network).

## strategy.json

`{theme, source, source_title, pillars: [{id, name, kind, cvs}], initiatives: [{id, pillar, title, evidence, journeys, procs, caps, apps, confidence}]}`.

## regulations.json

`[{id, name, short, status, dates: {key: date}, date_labels: {key: label}, main_date, date_note, articles_note, sources: [{title, url}], readiness, requirements: [{id, area, short, summary, articles, apps, caps, procs, size: S|M|L, deadline: date key, kind}]}]`.
Readiness is shown for regulations with dated requirements unless `readiness: false`. For rules that already apply (DORA, NIS2), use an internal remediation date as the deadline.

## scenarios.json

`[{id, name, type, targets, likelihood, pct, regulation, description, mitigation}]`. Types: `app_outage`, `platform_failure`, `supplier_failure`, `dc_loss`, `decommission`, `price_change`, `regulatory_change`.

## change_portfolio.json

`{epics: [{id, name, drivers, owner, summary}], features: [{id, epic, name, description, status, target: YYYY-Qn, size, owner, apps: {A..: New|Enhance|Configure|Integrate|Replace|Retire}, caps: [L3 ids], steps: [step ids], new_ifs: [{source, target, data}], drivers, depends}]}`. Drivers are initiative, requirement or programme decision IDs.

## programme.json (optional)

A merger, acquisition, divestment or transformation. The dashboard shows a programme view only when this file exists.

`{name, noun, kind, lens_label, decision_label, commitment_label, summary_title, summary, view_sub, timeline_title, completion, completion_label, timeline: [start, end], milestones: [{date, label, status: done|next|planned, ref}], phases: [{name, start: YYYY-Qn}], phase_notes, decisions: [{id: BDnn, title, apps, phase, options, hypothesis, criticality}], commitments: [{topic, stated, source, ref, implication, apps}], commitments_title, commitments_sub, synergy_title, synergy_note, synergy_defaults, lens_order, lens_colours, converge_sub, local_label, local_sub, local_match, partner_suppliers, change_of_control_note, sources}`

## glossary.json, versioning.json

`glossary`: organisation-specific terms `[{term, category, definition}]`, merged with the core and pack glossaries.
`versioning`: `{version, release_date, history: [{version, date, title, summary, source, changes: [{type, action, ids, text}]}]}`.
