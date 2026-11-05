# Outputs and behaviour

The engine produces every output from `repository/data.json`. Change the model, never the outputs.

## Dashboard

One self-contained HTML page: `repository/atlas_page.html` (publish this as the artifact, republishing to the same URL on every release) and `output/<prefix>_EA_Dashboard.html` (standalone, works offline or on an intranet). Load the artifact-design skill before changing the template, and the artifact-capabilities skill before publishing with saved scenarios and features.

Views, grouped in the left rail:

| Group | Views |
|---|---|
| Summary | Overview: movable KPI tiles that open the matching filtered view, strategy strip, TIME and confidence bars, programme lens (when a programme exists), needs-attention list |
| Strategy | Strategic priorities; the programme view (only when `programme.json` exists); Change impact; What if? |
| Business | Capability map with lenses (coverage, importance, maturity, technical risk, run cost, strategic focus, regulatory readiness, data confidence) and Show L3; Process architecture; Process maps (swimlanes); Value streams; Roles |
| Technology | Applications (TIME quadrant); Landscape map (colour by TIME, programme lens, confidence, criticality, readiness); Integration map (layers from the profile, colour by interface family); Resilience (sites from the model and its data centre model) |
| Commercial | Suppliers; Contracts and licences; Support and lifecycle; Third-party risk |
| Explore | Taxonomy and glossary; How to update; Change log; Traceability |

Behaviour: version badge opens the Change log; What's new strip on the overview; global search; a detail drawer for every element ending with Trace connections and Model what if; data confidence on every application and supplier; light and dark themes; usable at phone width; collapsible navigation (the [ key); movable overview tiles (pointer events, long press on touch, Alt and arrow keys); editors scroll into view with the cursor in the name field. Never call `history.replaceState` unguarded.

### What if?

Shared engine `scenario_engine.js` (dashboard, and node for the Excel), with an exact Python port in `impact_engine.py` for hosts without Node; `test_engine_parity.py` checks the two agree. Types: application outage, platform failure, supplier failure or exit, data centre loss, replace or decommission, supplier price change, regulatory change. Propagation: `runs_on` links, platforms that host a hosting prefix (`platform.hosts`) or carry a protocol (`platform.carries`), suppliers in any role, one hop of interfaces, and the data centre model (active-passive, active-active, single). Disruptions get an impact level and a risk rating; changes get a change size; price changes are rated relative to the total run cost. Saved scenarios use the artifact `db` capability with `user` for authorship, falling back to browser storage.

### Change impact

Shared engine `feature_engine.js`. Traces a feature's footprint to applications changed, partners to regression test or rework, platforms, L3 capabilities, journeys and steps, processes, roles to retrain and inform, customer exposure (customer-facing applications or customer steps), data domains, suppliers and contract ends, Tier 0 and 1 resilience, drivers, related requirements and initiatives, programme decisions (change twice risk) and contention. Rates Low, Medium, High or Critical against `change_thresholds`; calibrate the thresholds on the example backlog so the levels spread (roughly a quarter Low, a third Medium, a quarter High, the rest Critical). Checks: blockers for a dependency landing in the same quarter or later and a missed regulatory deadline; warnings for change twice risk, investment in Migrate or Eliminate applications, contention, contracts ending without auto-renewal, open DR issues; notes for the profile's criticality check, related requirements and new integrations.

### Regulatory readiness

Derived from the backlog: Not planned (no feature lists the requirement as a driver), Late (last feature lands after the deadline), On track, Done. Shown as a capability map lens and landscape colour (worst requirement, with a regulation picker when there are several), in application and capability drawers, and in the Excel requirements tab. Say that readiness is only as good as the backlog and that deadlines may be estimates.

## Excel repository

`output/<prefix>_EA_Repository.xlsx`, built by `build_xlsx.py` (openpyxl when installed, otherwise the built-in `mini_xlsx.py` writer: same tabs, values and formulas, plain formatting): README, Summary (formulas), one tab per entity and relationship, regulatory requirements with readiness, programme tabs when a programme exists, scenarios and impacts, epics, features and impacts, change log and change detail. Blue inputs for illustrative figures; formulas for utilisation, compliance, months to end of support, contract value, notice deadline and months since DR test. Recalculate with the xlsx skill's `recalc.py` (pass it to `build.py --recalc`) and check for zero formula errors. Tabs are laid out for import into EA tools.

## Copilot kit (optional)

When the user wants the atlas in Microsoft 365 Copilot: knowledge documents (Word) generated from `data.json`, a declarative agent with instructions of at most 8,000 characters, at most six conversation starters, a prompt pack and a setup guide. Copilot cannot run the engines, so its instructions must label new what-if and change impact answers as estimates. Rebuild the kit on every release once it exists.

## Prompt file

`output/<prefix>_EA_Atlas_Prompt.md` on every release: role, writing rules, organisation context, confirmed facts by confidence, pack and profile, scope, versioning, open questions. It lets anyone rebuild the atlas from scratch.
