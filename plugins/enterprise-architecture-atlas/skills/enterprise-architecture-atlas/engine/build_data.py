#!/usr/bin/env python3
"""Enterprise Architecture Atlas engine: builds repository/data.json from a model folder.

    python3 build_data.py --workspace path/to/ea-atlas

The model folder (workspace/model/*.json) holds everything that is specific to one organisation.
The industry pack named in model/organisation.json supplies the profile (labels and concepts such as
the capability standard, the criticality concept and third-party terms) and the industry glossary.
Nothing in this file is specific to an industry or an organisation.

Values the model does not supply (contract terms, licence and support figures, recovery targets,
fit and health scores) are generated from a seeded random generator and tagged Illustrative.
"""
import json, os, sys, random, glob, argparse, re, datetime as dt

ENGINE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(ENGINE)
PACKS = os.path.join(SKILL, "packs")
sys.path.insert(0, ENGINE)
import diff_snapshots, taxonomy as tax

ap = argparse.ArgumentParser()
ap.add_argument("--workspace", default=".", help="atlas workspace folder (contains model/)")
args = ap.parse_args()
WS = os.path.abspath(args.workspace)
MODEL = os.path.join(WS, "model")
REPO = os.path.join(WS, "repository")
os.makedirs(REPO, exist_ok=True)


def load(name, default):
    p = os.path.join(MODEL, name + ".json")
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_pack_file(pack, name, default):
    p = os.path.join(PACKS, pack, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def deep_merge(a, b):
    out = dict(a)
    for k, v in (b or {}).items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def dedup(xs):
    o = []
    for x in xs:
        if x not in o:
            o.append(x)
    return o


errs = []
ORG = load("organisation", None)
if ORG is None:
    sys.exit(f"No model/organisation.json in {WS}")
PACK = ORG.get("pack", "core")
PROFILE = deep_merge(load_pack_file("core", "profile.json", {}), load_pack_file(PACK, "profile.json", {}) if PACK != "core" else {})
PROFILE = deep_merge(PROFILE, ORG.get("profile", {}))
SEED = ORG.get("seed", 42)
rnd = random.Random(SEED)


def R(*key):
    """A generator of its own for each item, so illustrative figures depend only on that item and the seed:
    adding or changing one application does not shift the figures of any other."""
    return random.Random(f"{SEED}|" + "|".join(str(k) for k in key))
TODAY = dt.date.fromisoformat(ORG["as_of"])
SOURCES = ORG.get("sources", {})
SHORT = ORG.get("short_name", ORG["name"])
SCALE = float(ORG.get("cost_scale", 1.0))


def ref_of(r):
    """A ref may be a URL or a key into organisation.sources."""
    if not r:
        return ""
    return SOURCES.get(r, r) if not r.startswith("http") else r


# ---------------------------------------------------------------- capabilities
capabilities = []
for c in load("capabilities", []):
    c = dict(c)
    c.setdefault("parent", "")
    c.setdefault("description", "")
    c.setdefault("std_ref", "")
    c.setdefault("source", "Illustrative")
    c["level"] = 1 if not c["parent"] else 2
    if c["level"] == 2 and c.get("maturity") is None:
        c["maturity"] = R("maturity", c["id"]).choice([2, 2, 3, 3, 3, 4])
    if c["level"] == 1:
        c.setdefault("maturity", None)
    c.setdefault("importance", "Medium")
    capabilities.append(c)
cap_by = {c["id"]: c for c in capabilities}
for c in capabilities:
    if c["level"] == 2 and c["parent"] not in cap_by:
        errs.append(f"{c['id']} bad parent {c['parent']}")

# ---------------------------------------------------------------- roles
roles = []
for r in load("roles", []):
    r = dict(r)
    r.setdefault("source", "Illustrative")
    roles.append(r)
role_ids = {r["id"] for r in roles}
CUSTOMER_ROLE = ORG.get("customer_role") or next((r["id"] for r in roles if r.get("customer")), "")

# ---------------------------------------------------------------- suppliers
suppliers = []
for s in load("suppliers", []):
    s = dict(s)
    s["ref"] = ref_of(s.get("ref", ""))
    s.setdefault("material", False)
    s.setdefault("exit_plan", "Not documented")
    s.setdefault("risk", "Low")
    s.setdefault("tier", "Tactical")
    s.setdefault("hq", "To confirm")
    s.setdefault("location", "To confirm")
    s.setdefault("source", "Illustrative")
    suppliers.append(s)
sup_by = {s["id"]: s for s in suppliers}
INTERNAL = {s["id"] for s in suppliers if s.get("internal")}

# ---------------------------------------------------------------- hosting classes
HOSTING = ORG.get("hosting", {})


def host_info(h):
    if h in HOSTING:
        x = dict(HOSTING[h])
    else:
        x = {}
    if "kind" not in x:
        x["kind"] = ("vendor" if re.search(r"SaaS|Public cloud", h) and "on-prem" not in h.lower() else
                     "hybrid" if re.search(r"SaaS \+ on-prem|hybrid", h, re.I) else
                     "internal" if re.search(r"Private cloud|Mainframe|On-prem|Data centre|In-house", h, re.I) else
                     "end-user" if re.search(r"End-user", h, re.I) else "third-party")
    x.setdefault("licence_model", {"vendor": "SaaS subscription", "hybrid": "Subscription + term licence", "internal": "Term licence",
                                   "end-user": "Internal", "third-party": "Service fees"}[x["kind"]])
    x.setdefault("no_licence_cost", x["kind"] == "end-user")
    x.setdefault("evergreen", x["kind"] in ("vendor", "third-party"))
    x.setdefault("providers", [])
    return x


# ---------------------------------------------------------------- applications
OWN_BUS = ORG.get("owners_by_category", {})
OWN_TECH = ORG.get("tech_owners_by_category", {})
DEF_BUS = ORG.get("default_business_owner", "")
DEF_TECH = ORG.get("default_tech_owner", "")
FIT = {"Invest": ((3.4, 4.9), (3.3, 4.9)), "Tolerate": ((1.6, 2.9), (3.1, 4.3)), "Migrate": ((3.2, 4.7), (1.2, 2.8)), "Eliminate": ((1.1, 2.6), (1.1, 2.4))}
apps, app_supplier = [], []
for a in load("applications", []):
    a = dict(a)
    t = int(a.get("tier", 2))
    a["tier_n"] = t
    a["tier"] = f"Tier {t}"
    a.setdefault("lifecycle", "Production")
    a.setdefault("time", "Tolerate")
    a["crit"] = bool(a.pop("critical", a.pop("crit", False)))
    a.setdefault("source", "Illustrative")
    a["ref"] = ref_of(a.get("ref", ""))
    a.setdefault("programme_lens", "")
    a.setdefault("capabilities", [])
    a.setdefault("runs_on", [])
    a.setdefault("product", a["name"])
    users = R("users", a["id"]).randint(*{0: (1500, 3200), 1: (200, 2500), 2: (40, 600), 3: (10, 200)}[t])
    if "users" not in a:
        a["users"] = 0 if a.get("customer_facing") else users
    a["business_owner"] = a.get("business_owner") or OWN_BUS.get(a.get("category", ""), DEF_BUS)
    a["tech_owner"] = a.get("tech_owner") or OWN_TECH.get(a.get("category", ""), DEF_TECH)
    fr, hr = FIT[a["time"]]
    rf = R("fit", a["id"], a["time"])
    th, ff = round(rf.uniform(*hr), 1), round(rf.uniform(*fr), 1)
    a.setdefault("tech_health", th)
    a.setdefault("func_fit", ff)
    extra = a.pop("suppliers", [])
    apps.append(a)
    vend = a["vendor"]
    app_supplier.append(dict(app=a["id"], supplier=vend, role="In-house build" if vend in INTERNAL else "Product vendor"))
    for x in extra:
        app_supplier.append(dict(app=a["id"], supplier=x["supplier"], role=x["role"]))
    for p in host_info(a.get("hosting", "")).get("providers", []):
        if a["id"] in p.get("except_apps", []) or p["supplier"] == vend:
            continue
        if any(y["app"] == a["id"] and y["supplier"] == p["supplier"] for y in app_supplier):
            continue
        app_supplier.append(dict(app=a["id"], supplier=p["supplier"], role=p["role"]))
app_by_id = {a["id"]: a for a in apps}

# ---------------------------------------------------------------- L3 capabilities
capabilities_l3 = []
for l2, items in load("capabilities_l3", {}).items():
    if l2 not in cap_by:
        errs.append(f"L3 parent {l2} not an L2 capability")
        continue
    for n, it in enumerate(items, 1):
        if isinstance(it, dict):
            name, desc, aps, cid = it["name"], it.get("description", ""), it.get("apps"), it.get("id")
        else:
            name, desc, aps, cid = it[0], it[1], it[2], None
        aps = [x for x in (aps if aps is not None else [a["id"] for a in apps if l2 in a["capabilities"]]) if x in app_by_id]
        capabilities_l3.append(dict(id=cid or f"{l2}.{n:02d}", name=name, level=3, parent=l2, l1=cap_by[l2]["parent"], description=desc,
                                    apps=aps, coverage="Supported" if aps else "Gap", importance=cap_by[l2]["importance"],
                                    source=it.get("source", cap_by[l2]["source"]) if isinstance(it, dict) else cap_by[l2]["source"]))
        for x in aps:
            if l2 not in app_by_id[x]["capabilities"]:
                app_by_id[x]["capabilities"].append(l2)

# ---------------------------------------------------------------- contracts, licences, support
def cost_for(tier, key):
    base = {0: (1.0, 3.2), 1: (0.22, 0.85), 2: (0.05, 0.28), 3: (0.015, 0.08)}[tier]
    return round(R("cost", key, tier).uniform(*base) * SCALE, 2)


TP = PROFILE.get("third_party", {})
TERMS_VALUES = TP.get("terms_values", ["Yes", "Remediation in progress", "Gap", "N/A"])
contracts, licences, support = [], [], []
contract_by_sup = {}
ci = 0
for s in suppliers:
    if s["id"] in INTERNAL or s.get("no_contract"):
        continue
    ci += 1
    rk = R("contract", s["id"])
    start = dt.date(rk.randint(TODAY.year - 8, TODAY.year - 2), rk.randint(1, 12), 1)
    term = rk.choice([3, 3, 5, 5, 5, 7]) if s["tier"] == "Strategic" else rk.choice([3, 3, 5])
    end = dt.date(start.year + term, start.month, 1)
    while end < TODAY:
        end = dt.date(end.year + 3, end.month, 1)
    k = dict(id=f"K{ci:03d}", supplier=s["id"], title=f"{s['name']} master agreement", start=start.isoformat(), end=end.isoformat(),
             notice_months=rk.choice([3, 6, 6, 12]) if s["tier"] != "Strategic" else 12,
             auto_renew=rk.random() < 0.45,
             change_of_control_clause=s["tier"] in ("Strategic", "Important") and rk.random() < 0.7,
             regulatory_terms=rk.choice([TERMS_VALUES[0], TERMS_VALUES[0], TERMS_VALUES[1], TERMS_VALUES[2]]) if s["material"] else rk.choice([TERMS_VALUES[0], TERMS_VALUES[-1]]),
             annual_value=0.0, source="Illustrative")
    if s.get("contract"):
        k.update(s["contract"])
        k["source"] = s["contract"].get("source", s["source"])
    contract_by_sup[s["id"]] = k["id"]
    contracts.append(k)
contract_by_id = {k["id"]: k for k in contracts}

METRIC = ORG.get("licence_metric_by_category", {})
for a in apps:
    sup, t = a["vendor"], a["tier_n"]
    hi = host_info(a.get("hosting", ""))
    rl = R("licence", a["id"])
    lic_cost = 0.0 if hi["no_licence_cost"] else cost_for(t, a["id"])
    model = hi["licence_model"]
    supp_pct = 0.0 if re.search(r"SaaS|Consumption|fees|service|Subscription", model, re.I) and "term" not in model.lower() else round(rl.uniform(0.18, 0.22), 2)
    supp_cost = round(lic_cost * supp_pct, 2)
    metric = METRIC.get(a.get("category", ""), "Named users")
    ent = {0: lambda: rl.randint(800, 1500) * 1000, 1: lambda: rl.randint(50, 400) * 1000, 2: lambda: rl.randint(100, 900), 3: lambda: rl.randint(20, 250)}[t]()
    if metric in ("Named users", "Concurrent agents") and t <= 1:
        ent = rl.randint(300, 2500)
    util = rl.choice([0.55, 0.62, 0.71, 0.78, 0.84, 0.9, 0.94, 0.97, 1.04, 1.12])
    if hi["no_licence_cost"] or re.search(r"Statutory|Internal|commission", model, re.I):
        ent, util = 0, 0
    lic = dict(id=f"L{a['id'][1:]}", app=a["id"], contract=contract_by_sup.get(sup, ""), model=model, metric=metric, entitled=ent,
               consumed=int(ent * util), utilisation=round(util, 2), annual_cost_m=lic_cost, renewal="", compliance="", source="Illustrative")
    if a.get("licence"):
        lic.update(a.pop("licence"))
        if "consumed" not in lic or "utilisation" not in lic:
            pass
    if lic["entitled"] and "utilisation" in lic:
        lic["consumed"] = lic.get("consumed") or int(lic["entitled"] * lic["utilisation"])
    k = contract_by_id.get(lic["contract"])
    lic["renewal"] = lic.get("renewal") or (k["end"] if k else "")
    u = lic["utilisation"]
    lic["compliance"] = lic.get("compliance") or ("Over-deployed" if u > 1 else "Shelfware risk" if 0 < u < 0.65 else "Compliant" if u else "N/A")
    licences.append(lic)
    # support
    roles_here = [x for x in app_supplier if x["app"] == a["id"]]
    ams = next((x for x in roles_here if re.search(r"AMS", x["role"])), None)
    if sup in INTERNAL:
        smodel = "In-house"
    elif ams:
        smodel = f"Vendor + AMS ({sup_by[ams['supplier']]['name']})"
    elif hi["kind"] in ("vendor", "third-party"):
        smodel = "Vendor (SaaS or managed)"
    else:
        smodel = R("support", a["id"]).choice(["Vendor L3 + in-house L1/L2", "Vendor L3 + in-house L1/L2", "Managed service"])
    rh = R("hours", a["id"], t)
    hours = "24x7" if t == 0 else rh.choice(["24x7", "24x7", "Extended (7-22)"]) if t == 1 else rh.choice(["Business hours", "Extended (7-22)"])
    avail = {0: 99.95, 1: 99.9, 2: 99.5, 3: 99.0}[t]
    p1 = {0: "15 min / 4 h", 1: "30 min / 8 h", 2: "2 h / 1 BD", 3: "4 h / 2 BD"}[t]
    if a.get("end_of_support"):
        eos = a["end_of_support"]
    elif hi["evergreen"] and hi["kind"] != "internal":
        eos = "Evergreen (SaaS)"
    else:
        re_ = R("eos", a["id"])
        eos = dt.date(TODAY.year + 3 + re_.randint(0, 3), re_.randint(1, 12), 1).isoformat()
    version = "Current" if eos == "Evergreen (SaaS)" or eos > f"{TODAY.year + 2}" else ("N-1" if eos > f"{TODAY.year + 1}" else "N-2 or older")
    resolver = {"In-house": f"{SHORT} application support",
                "Vendor (SaaS or managed)": f"Vendor support + {SHORT} service desk (L1)",
                "Vendor L3 + in-house L1/L2": f"{SHORT} application support (L1/L2) + vendor (L3)",
                "Managed service": "Managed service provider"}.get(smodel, f"{sup_by[ams['supplier']]['name'] if ams else 'Vendor'} (L2/L3) + {SHORT} service desk (L1)")
    sp = dict(id=f"SP{a['id'][1:]}", app=a["id"], model=smodel, resolver=resolver, owner_role=a["tech_owner"], hours=hours,
              sla_availability=avail, sla_p1=p1, end_of_support=eos, version_currency=version, annual_support_cost_m=supp_cost, source="Illustrative")
    if a.get("support"):
        sp.update(a.pop("support"))
    support.append(sp)
for l in licences:
    k = contract_by_id.get(l["contract"])
    if k:
        sp = next(s for s in support if s["app"] == l["app"])
        k["annual_value"] = round(k["annual_value"] + l["annual_cost_m"] + sp["annual_support_cost_m"], 2)
for s in suppliers:
    if s.get("contract", {}).get("annual_value") is not None:
        k = contract_by_id.get(contract_by_sup.get(s["id"]))
        if k:
            k["annual_value"] = s["contract"]["annual_value"]

# ---------------------------------------------------------------- data centres and resilience
data_centres = ORG.get("data_centres", [])
DC_MODEL = ORG.get("dc_model", "active-passive" if len(data_centres) >= 2 else "single")
prim = next((d for d in data_centres if d.get("kind") == "primary"), data_centres[0] if data_centres else None)
sec_ = next((d for d in data_centres if d.get("kind") == "secondary"), data_centres[1] if len(data_centres) > 1 else None)
dc_text = (f"{prim['name']} (primary)" + (f", {sec_['name']} (secondary)" if sec_ else "")) if prim else "In-house site"
mode_text = ({"active-passive": f"Active-passive: {prim['name']} live, {sec_['name']} standby" if prim and sec_ else "Single site",
              "active-active": f"Active-active: {prim['name']} and {sec_['name']} both live" if prim and sec_ else "Single site",
              "single": f"Single site: {prim['name']}" if prim else "Single site"}[DC_MODEL])
RTO = {int(k): tuple(v) for k, v in PROFILE.get("recovery_targets", {"0": [2, 15], "1": [4, 60], "2": [24, 240], "3": [72, 1440]}).items()}
resilience = []
for a in apps:
    hi = host_info(a.get("hosting", ""))
    kind = hi["kind"]
    a["site"] = "internal" if kind in ("internal",) else "vendor" if kind in ("vendor", "hybrid") else "end-user" if kind == "end-user" else "third-party"
    a.setdefault("data_centres", dc_text if kind == "internal" else ("Vendor cloud" + (f" + {dc_text}" if kind == "hybrid" else "")) if kind in ("vendor", "hybrid")
                 else "End-user devices" if kind == "end-user" else f"Third-party site ({a.get('hosting', '')})")
    a["dc_mode"] = mode_text if a["site"] == "internal" else "Vendor-managed resilience" if a["site"] == "vendor" else "Third-party managed"
    rto, rpo = RTO[a["tier_n"]]
    if a["site"] == "internal":
        rd = R("dr", a["id"], a["tier_n"] <= 1)
        last = TODAY - dt.timedelta(days=rd.randint(60, 560))
        result = rd.choice(["Passed", "Passed", "Passed", "Passed with issues", "Failed"]) if a["tier_n"] <= 1 else rd.choice(["Passed", "Passed with issues", "Not tested"])
        if result == "Not tested":
            last = None
        failover = {"active-passive": "Manual site failover", "active-active": "Automatic (active-active)", "single": "Restore from backup"}[DC_MODEL]
    else:
        last, result, failover = None, "Vendor attestation", "Vendor-managed" if a["site"] == "vendor" else "Third-party"
    r = dict(app=a["id"], site=a["site"], mode=a["dc_mode"], rto_hours=rto, rpo_minutes=rpo, last_dr_test=last.isoformat() if last else "",
             dr_result=result, failover_type=failover, source="Illustrative")
    if a.get("resilience"):
        r.update(a.pop("resilience"))
    resilience.append(r)

# ---------------------------------------------------------------- value streams, journeys, steps
VSM = load("value_streams", {"customer_value_streams": [], "journeys": []})
customer_value_streams = []
for c in VSM["customer_value_streams"]:
    c = dict(c)
    c["ref"] = ref_of(c.get("ref", ""))
    c.setdefault("source", "Illustrative")
    c.setdefault("cross_cutting", False)
    customer_value_streams.append(c)
value_streams, steps = [], []
for j in VSM["journeys"]:
    j = dict(j)
    sts = j.pop("steps", [])
    j.setdefault("source", "Illustrative")
    value_streams.append(j)
    for i, s in enumerate(sts, 1):
        steps.append(dict(id=f"{j['id']}.{i}", vs=j["id"], seq=i, name=s["name"], capabilities=s.get("capabilities", []), apps=dedup(s.get("apps", [])),
                          R=s.get("R", []), A=s["A"], C=s.get("C", []), I=s.get("I", [])))

# ---------------------------------------------------------------- business processes, data, interfaces
business_processes = []
for p in load("processes", []):
    p = dict(p)
    p.setdefault("parent", "")
    p["level"] = 1 if not p["parent"] else 2
    for k in ("roles", "capabilities", "apps", "journeys"):
        p[k] = dedup(p.get(k, []))
    p.setdefault("source", "Illustrative")
    business_processes.append(p)
data_domains = []
for d in load("data_domains", []):
    d = dict(d)
    d["consumers"] = dedup(d.get("consumers", []))
    d.setdefault("source", "Illustrative")
    data_domains.append(d)
interfaces = []
for i, x in enumerate(load("interfaces", []), 1):
    x = dict(x)
    x.setdefault("id", f"I{i:03d}")
    x.setdefault("frequency", "To confirm")
    interfaces.append(x)

# ---------------------------------------------------------------- strategy, regulation, scenarios, change, programme
STRATEGY = load("strategy", {"theme": "", "pillars": [], "initiatives": []})
STRATEGY["source"] = ref_of(STRATEGY.get("source", ""))
REGULATIONS = load("regulations", [])
EXAMPLE_SCENARIOS = load("scenarios", [])
CHANGE = load("change_portfolio", {"epics": [], "features": []})
PROGRAMME = load("programme", None)

# ---------------------------------------------------------------- validation
cap_ids = {c["id"] for c in capabilities}
sup_ids = {s["id"] for s in suppliers}
bp_ids = {b["id"] for b in business_processes}
for a in apps:
    for c in a["capabilities"]:
        if c not in cap_ids: errs.append(f"{a['id']} bad cap {c}")
    if a["vendor"] not in sup_ids: errs.append(f"{a['id']} bad vendor {a['vendor']}")
    for x in a["runs_on"]:
        if x["app"] not in app_by_id: errs.append(f"{a['id']} runs on unknown app {x['app']}")
    for k in ("business_owner", "tech_owner"):
        if a[k] and a[k] not in role_ids: errs.append(f"{a['id']} bad {k} {a[k]}")
for x in app_supplier:
    if x["supplier"] not in sup_ids: errs.append(f"{x['app']} bad supplier {x['supplier']}")
for s in steps:
    for c in s["capabilities"]:
        if c not in cap_ids: errs.append(f"{s['id']} bad cap {c}")
    for x in s["apps"]:
        if x not in app_by_id: errs.append(f"{s['id']} bad app {x}")
    for r in s["R"] + s["C"] + s["I"] + [s["A"]]:
        if r not in role_ids: errs.append(f"{s['id']} bad role {r}")
cvs_ids = {c["id"] for c in customer_value_streams}
for v in value_streams:
    if v["parent"] not in cvs_ids: errs.append(f"{v['id']} bad value stream {v['parent']}")
    if v["owner"] not in role_ids: errs.append(f"{v['id']} bad owner")
for c in customer_value_streams:
    if c["owner"] not in role_ids: errs.append(f"{c['id']} bad owner")
for bp in business_processes:
    for x in bp["apps"]:
        if x not in app_by_id: errs.append(f"{bp['id']} bad app {x}")
    for c in bp["capabilities"]:
        if c not in cap_ids: errs.append(f"{bp['id']} bad cap {c}")
    for r in [bp["owner"]] + bp["roles"]:
        if r not in role_ids: errs.append(f"{bp['id']} bad role {r}")
    for j in bp["journeys"]:
        if j not in {v["id"] for v in value_streams}: errs.append(f"{bp['id']} bad journey {j}")
for i in interfaces:
    for x in (i["source_app"], i["target_app"]):
        if x not in app_by_id: errs.append(f"{i['id']} bad app {x}")
for d in data_domains:
    for x in [d["sor"]] + d["consumers"]:
        if x not in app_by_id: errs.append(f"{d['id']} bad app {x}")
    if d.get("steward") and d["steward"] not in role_ids: errs.append(f"{d['id']} bad steward")
for r in REGULATIONS:
    for q in r["requirements"]:
        for x in q["apps"]:
            if x not in app_by_id: errs.append(f"{q['id']} bad app {x}")
        for c in q["caps"]:
            if c not in cap_ids: errs.append(f"{q['id']} bad cap {c}")
        for b in q["procs"]:
            if b not in bp_ids: errs.append(f"{q['id']} bad proc {b}")
for si in STRATEGY["initiatives"]:
    for x in si["apps"]:
        if x not in app_by_id: errs.append(f"{si['id']} bad app {x}")
    for c in si["caps"]:
        if c not in cap_ids: errs.append(f"{si['id']} bad cap {c}")
    for b in si["procs"]:
        if b not in bp_ids: errs.append(f"{si['id']} bad proc {b}")
    for j in si.get("journeys", []):
        if j not in {v["id"] for v in value_streams}: errs.append(f"{si['id']} bad journey {j}")
if PROGRAMME:
    for d in PROGRAMME.get("decisions", []) + PROGRAMME.get("commitments", []):
        d["apps"] = dedup(d.get("apps", []))
        for x in d["apps"]:
            if x not in app_by_id: errs.append(f"programme {d.get('id', d.get('topic'))} bad app {x}")
    for s in PROGRAMME.get("partner_suppliers", []):
        if s not in sup_ids: errs.append(f"programme partner supplier {s} unknown")
for a in apps:
    if not any(l["app"] == a["id"] for l in licences): errs.append(f"{a['id']} no licence")
    if not any(s["app"] == a["id"] for s in support): errs.append(f"{a['id']} no support")
# every step has exactly one accountable role by construction (A is a single field)
apps_in_proc = {x for bp in business_processes for x in bp["apps"]} | {x for st in steps for x in st["apps"]}
apps_without_process = [a["id"] for a in apps if a["id"] not in apps_in_proc]
l2_no_app = [c["id"] for c in capabilities if c["level"] == 2 and not any(c["id"] in a["capabilities"] for a in apps)]


def conf(src):
    if src.startswith("Customer-provided"): return "Customer-provided"
    if src.startswith("Public") and "Illustrative" not in src and "confirm" not in src: return "Public"
    if "Public" in src or "confirm" in src: return "Partly confirmed"
    return "Illustrative"


for coll in (apps, suppliers):
    for x in coll:
        x["confidence"] = conf(x["source"])

# strategic focus count per capability
cap_imp = {}
for si in STRATEGY["initiatives"]:
    for c in si["caps"]:
        cap_imp[c] = cap_imp.get(c, 0) + 1
for c in capabilities:
    c["strategic_initiatives"] = cap_imp.get(c["id"], 0)

# ---------------------------------------------------------------- change portfolio
STATUSES = ["Idea", "Discovery", "Ready", "In delivery", "Done"]
CHANGE_TYPES = ["New", "Enhance", "Configure", "Integrate", "Replace", "Retire"]
l3ids = {c["id"] for c in capabilities_l3}
stepids = {x["id"] for x in steps}
drivers_ok = {i["id"] for i in STRATEGY["initiatives"]} | {q["id"] for r in REGULATIONS for q in r["requirements"]} | {d["id"] for d in (PROGRAMME or {}).get("decisions", [])}
epics = [dict(e, source=e.get("source", "Illustrative")) for e in CHANGE.get("epics", [])]
features = [dict(f, source=f.get("source", "Illustrative")) for f in CHANGE.get("features", [])]
fids, eids = {f["id"] for f in features}, {e["id"] for e in epics}
for f in features:
    for k in ("caps", "steps", "new_ifs", "drivers", "depends"):
        f.setdefault(k, [])
    if f["epic"] not in eids: errs.append(f"{f['id']} bad epic")
    if f["owner"] not in role_ids: errs.append(f"{f['id']} bad owner")
    if f["status"] not in STATUSES: errs.append(f"{f['id']} bad status")
    for a_, c_ in f["apps"].items():
        if a_ not in app_by_id: errs.append(f"{f['id']} bad app {a_}")
        if c_ not in CHANGE_TYPES: errs.append(f"{f['id']} bad change type {c_}")
    for c_ in f["caps"]:
        if c_ not in l3ids: errs.append(f"{f['id']} bad L3 {c_}")
    for s_ in f["steps"]:
        if s_ not in stepids: errs.append(f"{f['id']} bad step {s_}")
    for d_ in f["drivers"]:
        if d_ not in drivers_ok: errs.append(f"{f['id']} bad driver {d_}")
    for d_ in f["depends"]:
        if d_ not in fids: errs.append(f"{f['id']} bad dependency {d_}")
    for n_ in f["new_ifs"]:
        if n_["source"] not in app_by_id or n_["target"] not in app_by_id: errs.append(f"{f['id']} bad new interface")
for e in epics:
    if e["owner"] not in role_ids: errs.append(f"{e['id']} bad owner")
    for d_ in e["drivers"]:
        if d_ not in drivers_ok: errs.append(f"{e['id']} bad driver {d_}")
for sc in EXAMPLE_SCENARIOS:
    pool = {"app": app_by_id, "sup": sup_ids, "dc": {d["id"] for d in data_centres}}
    if sc["type"] == "regulatory_change" and sc.get("regulation") not in {r["id"] for r in REGULATIONS}:
        errs.append(f"{sc['id']} bad regulation")

# ---------------------------------------------------------------- glossary, taxonomy
gloss = {}
for src in (load_pack_file("core", "glossary.json", []), load_pack_file(PACK, "glossary.json", []) if PACK != "core" else [], load("glossary", [])):
    for g in src:
        gloss[g["term"]] = g
glossary = [dict(id=f"G{i:03d}", term=g["term"], category=g["category"], definition=g["definition"]) for i, g in enumerate(sorted(gloss.values(), key=lambda g: (g["category"], g["term"])), 1)]
taxonomy, relationships = tax.build(PROFILE, ORG, PROGRAMME)

meta = dict(organisation=ORG["name"], short_name=SHORT, as_of=TODAY.isoformat(), context=ORG.get("context", []), sources=SOURCES,
            disclaimer=ORG.get("disclaimer", f"Illustrative reference model. Items tagged Public are drawn from public sources; costs, dates, SLAs, utilisation and assessments are illustrative until replaced with {SHORT} data."),
            pack=PACK, profile=PROFILE, currency=ORG.get("currency", {"symbol": "€", "code": "EUR"}), dc_model=DC_MODEL,
            customer_role=CUSTOMER_ROLE, change_thresholds=ORG.get("change_thresholds", [15, 30, 50]), dashboard_title=ORG.get("dashboard_title", f"{SHORT} Atlas"),
            storage_key=re.sub(r"[^a-z0-9]+", "-", SHORT.lower()).strip("-") + "-atlas",
            file_prefix=ORG.get("file_prefix", re.sub(r"[^A-Za-z0-9]+", "_", SHORT).strip("_")),
            validation=dict(errors=errs, l2_without_app=l2_no_app), apps_without_process=apps_without_process)

data = dict(meta=meta, strategy=STRATEGY, regulations=REGULATIONS, example_scenarios=EXAMPLE_SCENARIOS, taxonomy=taxonomy, relationships=relationships,
            glossary=glossary, data_centres=data_centres, resilience=resilience, programme=PROGRAMME, business_processes=business_processes,
            capabilities=capabilities, capabilities_l3=capabilities_l3, epics=epics, features=features, customer_value_streams=customer_value_streams,
            value_streams=value_streams, steps=steps, roles=roles, apps=apps, suppliers=suppliers, app_supplier=app_supplier, contracts=contracts,
            licences=licences, support=support, data_domains=data_domains, interfaces=interfaces)

# ---------------------------------------------------------------- versioning: snapshot and automatic diff
VER = load("versioning", {"version": "1.0", "release_date": TODAY.isoformat(), "history": []})
vt = lambda v: tuple(int(x) for x in v.split("."))
vdir = os.path.join(REPO, "versions")
os.makedirs(vdir, exist_ok=True)
data["meta"]["version"] = VER["version"]
data["meta"]["release_date"] = VER["release_date"]
if not any(h["version"] == VER["version"] for h in VER["history"]):
    errs.append(f"versioning.json has no history entry for {VER['version']}")
hist = [dict(h) for h in VER["history"]]
snaps = sorted([os.path.basename(f)[1:-5] for f in glob.glob(os.path.join(vdir, "v*.json"))], key=vt)
for h in hist:
    h.setdefault("changes", [])
    prev = [v for v in snaps if vt(v) < vt(h["version"])]
    if h["version"] == VER["version"] and prev:
        old = json.load(open(os.path.join(vdir, f"v{prev[-1]}.json")))
        ch = diff_snapshots.diff(old, data)
        h["diff_from"], h["diff"], h["diff_summary"] = prev[-1], ch, diff_snapshots.summarise(ch)
    elif os.path.exists(os.path.join(vdir, f"v{h['version']}.json")) and prev:
        old = json.load(open(os.path.join(vdir, f"v{prev[-1]}.json")))
        cur = json.load(open(os.path.join(vdir, f"v{h['version']}.json")))
        ch = diff_snapshots.diff(old, cur)
        h["diff_from"], h["diff"], h["diff_summary"] = prev[-1], ch, diff_snapshots.summarise(ch)
# detected changes of past releases are kept in model/_release_diffs.json, so the change log survives when the
# workspace travels as one atlas file that carries only the latest snapshot
RD_PATH = os.path.join(MODEL, "_release_diffs.json")
stored = load("_release_diffs", {})
for h in hist:
    if "diff" in h:
        stored[h["version"]] = dict(diff_from=h["diff_from"], diff=h["diff"], diff_summary=h["diff_summary"])
    elif h["version"] in stored:
        h.update(stored[h["version"]])
stored = {v: x for v, x in stored.items() if any(h["version"] == v for h in hist)}
if stored:
    json.dump(stored, open(RD_PATH, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
data["changelog"] = sorted(hist, key=lambda h: vt(h["version"]), reverse=True)
snap = dict(data)
snap.pop("changelog", None)
json.dump(snap, open(os.path.join(vdir, f"v{VER['version']}.json"), "w"), separators=(",", ":"))
json.dump(data, open(os.path.join(REPO, "data.json"), "w"), indent=1, ensure_ascii=False)

cur = data["meta"]["currency"]["symbol"]
print("workspace", WS, "pack", PACK, "version", VER["version"])
print("caps", len([c for c in capabilities if c["level"] == 2]), "L3", len(capabilities_l3), "apps", len(apps), "sups", len(suppliers), "steps", len(steps),
      "roles", len(roles), "ifs", len(interfaces), "processes", len(business_processes), "features", len(features))
print("diff entries", len(next((h.get("diff", []) for h in hist if h["version"] == VER["version"]), [])))
print("errors", errs)
print("L2 with no app", l2_no_app)
print("apps without process", apps_without_process)
print(f"total licence {cur}m", round(sum(l["annual_cost_m"] for l in licences), 1), f"support {cur}m", round(sum(s["annual_support_cost_m"] for s in support), 1))
