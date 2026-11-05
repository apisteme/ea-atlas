# Industry packs

A pack holds everything that is specific to an industry but not to one organisation. The engine reads the pack's `profile.json` and `glossary.json` at build time. The other files are templates that seed a new workspace (`engine/pack_tools.py new-workspace`), after which the organisation's model is the source of truth.

| File | Purpose |
|---|---|
| `profile.json` | Labels and concepts the engine and dashboard use (see below) |
| `capabilities.json`, `capabilities_l3.json` | Reference capability model, L1 to L3, with `std_ref` naming the standard's domain |
| `roles.json` | Typical roles, including technology, data and security roles |
| `value_streams.json` | Typical value streams and journeys with steps, capabilities and RACI (no applications) |
| `processes.json` | Operate, Manage and Support process hierarchy with capabilities (no applications) |
| `regulations.json` | Regulation library: requirements with suggested capabilities and dates; applications and processes are mapped per organisation |
| `glossary.json` | Industry terms (the core pack holds the architecture and portfolio terms) |
| `README.md` | Standards used, licence notes, sources |

## profile.json

| Key | Used for |
|---|---|
| `id`, `name`, `org_noun` | Pack identity; "the bank", "the insurer", "the organisation" in text |
| `value_stream_label` | What value streams are called |
| `capability_standard` | `{name, short, ref_label, note}`: capability map subtitle and the label of `std_ref` |
| `process_framework`, `process_tiers` | Process architecture subtitle and tier descriptions |
| `criticality` | `{label, short, plural, abbr, help, regime, flag_kind, change_flag}`: the concept behind the `critical` flag on applications (DORA critical or important function, business-critical service, essential service under NIS2) and the check raised when a change touches one |
| `third_party` | `{material_label, material_abbr, terms_label, terms_values, register, guidance, view_sub}`: the `material` flag on suppliers and the contract terms column |
| `resilience` | `{regime, note}` |
| `recovery_targets` | Illustrative RTO hours and RPO minutes by tier |
| `layers` | Integration map columns: `[[layer name, [application categories]]]`; unknown categories go in the last layer |
| `interface_families` | `[{name, match (regex), var (colour token)}]`; the first match wins, so put the catch-all last |
| `taxonomy_examples` | Industry examples in the taxonomy view |

Anything not set falls back to the core profile, and an organisation can override any key in `organisation.json` → `profile`.

## Writing a new pack

1. Copy `packs/core` to `packs/<industry>` and edit `profile.json` first: the criticality concept, third-party terms and layers matter most.
2. Write the capability model in your own words. Record the standard's domain or service name in `std_ref`. Many industry standards are licensed to members (TM Forum, ACORD, parts of BIAN): do not copy their text or numbering unless the licence allows it. APQC PCF and CAUDIT HERM are more open; check current terms.
3. Aim for 8 to 12 L1, 40 to 80 L2, two to five L3 per L2.
4. Add roles covering the business and technology, journeys for the main customer outcomes, and the process hierarchy.
5. Add regulations with dated requirements and suggested capabilities. Verify every date and status at the time of writing and cite sources.
6. Run `python3 engine/pack_tools.py validate <industry>`; fix every error.
7. Seed a test workspace with `new-workspace`, add a handful of applications, build, and run the smoke test.

## Suggested standards by industry

| Industry | Capability and process references | Typical regulatory lens |
|---|---|---|
| Banking | BIAN service domains, APQC PCF banking | DORA, PSR and PSD3, AML, Basel and CRR, AI Act |
| Insurance | ACORD-style domains, APQC PCF insurance | Solvency II, DORA, IDD, IFRS 17, AI Act |
| Telecoms | TM Forum eTOM, SID, ODA components | NIS2, telecoms security rules, EECC |
| Healthcare | HL7 FHIR resources, national health capability models | Data protection, medical device software rules, clinical safety standards |
| Energy and utilities | IEC CIM, utility reference models | NIS2, critical entities rules, sector regulator rules |
| Manufacturing | ISA-95, SCOR | NIS2, IEC 62443, product safety |
| Retail | APQC PCF retail, NRF ARTS | PCI DSS, consumer law, data protection |
| Public sector | National government capability models, service standards | Cyber assessment frameworks, technology codes of practice |
| Higher education | CAUDIT HERM | Sector regulator conditions, data protection |
| Pharma and life sciences | APQC PCF pharma | GxP, computerised system validation rules |
