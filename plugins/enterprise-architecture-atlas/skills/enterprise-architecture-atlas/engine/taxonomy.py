"""Element taxonomy and relationship list for the atlas. Labels come from the industry profile, so the
same metamodel reads naturally for a bank, an insurer, a utility or a public body."""


def build(P, ORG, programme):
    has_programme = bool(programme)
    org = ORG.get("short_name", ORG["name"])
    noun = P.get("org_noun", "organisation")
    std = P.get("capability_standard", {}).get("name", "a reference capability model")
    pf = P.get("process_framework", "APQC PCF")
    crit = P.get("criticality", {})
    ex = P.get("taxonomy_examples", {})
    vsl = P.get("value_stream_label", "Value stream")
    prog = programme or {}
    T = [
        ("Business", vsl, "L0", "CVS", f"A customer-facing outcome {org} organises itself around.", ex.get("value_stream", "Customer onboarding"), ""),
        ("Business", "Journey", "L1", "VS", "An end-to-end customer or business journey inside a value stream, from trigger to outcome.", ex.get("journey", "Register a claim"), vsl),
        ("Business", "Process step", "L3", "VSnn.n", "One activity in a journey. Carries RACI, the applications used and the capabilities it realises.", ex.get("step", "Assess and approve"), "Journey"),
        ("Business", "Process category", "L0", "", f"The top tier of the process hierarchy: Operate (serves customers), Manage (directs and controls), Support (keeps the {noun} running).", "Operate", ""),
        ("Business", "Process group", "L1", "P", f"A group of related processes, aligned to {pf}.", ex.get("process_group", "Manage risk and compliance"), "Process category"),
        ("Business", "Process", "L2", "Pn.n", "A repeatable business process with an owner, applications and capabilities. Operate processes link to journeys.", ex.get("process", "Regulatory reporting"), "Process group"),
        ("Business", "Capability domain", "L1", "Cnn", f"A broad area of what the {noun} does, independent of organisation and systems.", ex.get("cap_l1", "Customer management"), ""),
        ("Business", "Capability", "L2", "Cnn.nn", f"A specific ability the {noun} needs, aligned to {std}. Stable over time even when processes and systems change.", ex.get("cap_l2", "Customer onboarding"), "Capability domain"),
        ("Business", "Capability (L3)", "L3", "Cnn.nn.nn", "A specific ability inside an L2 capability, mapped to the applications that realise it; an L3 with no application is a gap.", ex.get("cap_l3", "Identity verification"), "Capability"),
        ("Change", "Epic", "", "EPnn", "A large piece of change that serves one or more strategic initiatives, regulatory requirements" + (f" or {prog.get('decision_label', 'programme decisions').lower()}" if has_programme else "") + ", delivered as several features.", ex.get("epic", "Digital self-service"), ""),
        ("Change", "Feature", "", "Fnnn", "A deliverable change with a target quarter and status. Its footprint names the applications it changes and how (new, enhance, configure, integrate, replace, retire), the L3 capabilities and the journey steps whose way of working changes. The atlas traces its impact from that footprint.", ex.get("feature", "Online claim form"), "Epic"),
        ("Business", "Role", "", "R", "A job role or external party that performs process steps. Linked through RACI.", ex.get("role", "Claims handler"), ""),
        ("Technology", "Application", "", "A", f"A software system or service the {noun} uses or depends on, including platforms and partner-hosted services.", ex.get("app", "Policy administration system"), ""),
        ("Technology", "Platform application", "", "A", "An application other applications run on. Linked through 'runs on' with a status.", ex.get("platform", "Container platform"), "Application"),
        ("Technology", "Interface", "", "I", "A data flow from one application to another, with its data, integration type and frequency.", ex.get("interface", "Policy data to finance (file)"), ""),
        ("Technology", "Data domain", "", "D", "A business data subject with one system of record and several consumers.", ex.get("data_domain", "Customer"), ""),
        ("Technology", "Data centre", "", "DC", f"A physical site that hosts {org} workloads.", ex.get("dc", "Primary data centre"), ""),
        ("Commercial", "Supplier", "", "S", "A third party that provides software, services, hosting or a partnership.", ex.get("supplier", "Hosting provider"), ""),
        ("Commercial", "Contract", "", "K", "The master agreement with a supplier: term, notice, renewal and key clauses.", "K001 master agreement", "Supplier"),
        ("Commercial", "Licence", "", "L", "The licence or subscription for one application: model, metric, entitlement, usage and cost.", "Per-core subscription", "Contract"),
        ("Commercial", "Support agreement", "", "SP", "How one application is supported: resolver groups, hours, SLAs and vendor end of support.", f"Vendor (L3) + {org} service desk (L1)", "Application"),
        ("Strategy", "Strategic pillar", "", "SP", f"One of {org}'s strategic priorities or goals.", ex.get("pillar", "Customer satisfaction"), ""),
        ("Strategy", "Strategic initiative", "", "SI", "A strategic achievement or programme under a pillar, traced to the journeys, processes, capabilities and applications it depends on.", ex.get("initiative", "Digital claims"), "Strategic pillar"),
        ("Strategy", "Scenario", "", "EX / sc", "A modelled disruption, change or regulation, with the items it affects. The impact is computed from the repository, so it stays current as the data changes.", ex.get("scenario", "Loss of the primary data centre"), ""),
        ("Strategy", "Regulatory requirement", "", "REG-nn", "One obligation from a regulation, mapped to the applications, capabilities and processes that must change.", ex.get("requirement", "Incident reporting within set deadlines"), "Scenario"),
    ]
    if has_programme:
        dl = prog.get("decision_label", "Programme decision")
        T += [("Strategy", dl, "", "BD", f"A key platform decision raised by the {prog.get('noun', 'programme')}, with options, an EA hypothesis, a phase and a blast radius.", ex.get("decision", "Consolidate policy administration"), ""),
              ("Strategy", prog.get("commitment_label", "Programme commitment"), "", "", "A stated position or commitment, paraphrased, with its architecture implication.", ex.get("commitment", "One back office for all product lines"), "")]
    R = [
        ("Epic", "serves", "Strategic initiative, Regulatory requirement" + (f" or {prog.get('decision_label', 'Programme decision')}" if has_programme else "")),
        ("Epic", "is delivered by", "Feature"),
        ("Feature", "changes", "Application (with a change type)"),
        ("Feature", "creates or changes", "Capability (L3)"),
        ("Feature", "changes the way of working in", "Process step"),
        ("Feature", "depends on", "Feature"),
        (vsl, "contains", "Journey"),
        ("Journey", "is made of", "Process step"),
        ("Role", "is R, A, C or I for", "Process step"),
        ("Process step", "realises", "Capability"),
        ("Process step", "uses", "Application"),
        ("Process", "covers", "Journey"),
        ("Process", "is supported by", "Application"),
        ("Application", "supports", "Capability"),
        ("Application", "runs on", "Platform application"),
        ("Application", "is hosted in", "Data centre"),
        ("Application", "is supplied by", "Supplier (vendor, SI, AMS, hosting, platform)"),
        ("Application", "sends data to", "Application (Interface)"),
        ("Data domain", "has system of record", "Application"),
        ("Supplier", "is governed by", "Contract"),
        ("Contract", "covers", "Licence"),
        ("Application", "is covered by", "Support agreement"),
    ]
    if has_programme:
        R.append((prog.get("decision_label", "Programme decision"), "affects", "Application"))
    taxonomy = [dict(domain=a, element=b, level=c, prefix=d, definition=e, example=f, parent=g) for a, b, c, d, e, f, g in T]
    relationships = [dict(source=a, verb=b, target=c) for a, b, c in R]
    return taxonomy, relationships
