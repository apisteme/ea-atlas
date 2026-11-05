#!/usr/bin/env python3
"""Industry pack tools.

    python3 pack_tools.py list
    python3 pack_tools.py validate [PACK ...]
    python3 pack_tools.py new-workspace --pack insurance --name "Example Insurer" --short Example --out path/to/ea-atlas

validate  checks a pack's internal references: capability parents, L3 keys, roles, capabilities and journeys
          used by the templates and the regulation library, and the profile keys the engine reads.
new-workspace  creates an atlas workspace (folders, model files seeded from the pack templates, an
          organisation.json to complete, a versioning.json at 1.0). Applications, suppliers and interfaces
          start empty: they come from the organisation (inventory, Archi import, research) during Build mode.
"""
import argparse, json, os, sys, datetime as dt
E = os.path.dirname(os.path.abspath(__file__))
PACKS = os.path.join(os.path.dirname(E), "packs")
FILES = ["profile.json", "capabilities.json", "capabilities_l3.json", "roles.json", "value_streams.json", "processes.json", "regulations.json", "glossary.json"]
PROFILE_KEYS = ["id", "name", "org_noun", "capability_standard", "process_framework", "criticality", "third_party"]


def load(pack, f, default=None):
    p = os.path.join(PACKS, pack, f)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def validate(pack):
    errs, warn = [], []
    for f in FILES:
        if not os.path.exists(os.path.join(PACKS, pack, f)):
            (errs if f in ("profile.json", "capabilities.json") else warn).append(f"missing {f}")
    prof = load(pack, "profile.json", {})
    for k in PROFILE_KEYS:
        if pack != "core" and k not in prof and k not in load("core", "profile.json", {}):
            errs.append(f"profile missing {k}")
    caps = load(pack, "capabilities.json", [])
    ids = {c["id"] for c in caps}
    for c in caps:
        if c.get("parent") and c["parent"] not in ids:
            errs.append(f"capability {c['id']} has unknown parent {c['parent']}")
    l2 = {c["id"] for c in caps if c.get("parent")}
    l3 = load(pack, "capabilities_l3.json", {})
    l3ids = set()
    for k, v in l3.items():
        if k not in l2:
            errs.append(f"L3 group {k} is not an L2 capability")
        for i, _ in enumerate(v, 1):
            l3ids.add(f"{k}.{i:02d}")
    roles = {r["id"] for r in load(pack, "roles.json", [])}
    vs = load(pack, "value_streams.json", {"customer_value_streams": [], "journeys": []})
    cvs = {c["id"] for c in vs["customer_value_streams"]}
    js = {j["id"] for j in vs["journeys"]}
    for c in vs["customer_value_streams"]:
        if roles and c["owner"] not in roles: errs.append(f"{c['id']} owner {c['owner']} not a role")
    for j in vs["journeys"]:
        if j["parent"] not in cvs: errs.append(f"{j['id']} parent {j['parent']} not a value stream")
        if roles and j["owner"] not in roles: errs.append(f"{j['id']} owner not a role")
        for s in j["steps"]:
            for c in s["capabilities"]:
                if c not in ids: errs.append(f"{j['id']} step '{s['name']}' unknown capability {c}")
            for r in s["R"] + s["C"] + s["I"] + [s["A"]]:
                if roles and r not in roles: errs.append(f"{j['id']} step '{s['name']}' unknown role {r}")
    for p in load(pack, "processes.json", []):
        if roles and p["owner"] not in roles: errs.append(f"{p['id']} owner not a role")
        for r in p.get("roles", []):
            if roles and r not in roles: errs.append(f"{p['id']} unknown role {r}")
        for c in p.get("capabilities", []):
            if c not in ids: errs.append(f"{p['id']} unknown capability {c}")
        for j in p.get("journeys", []):
            if j not in js: errs.append(f"{p['id']} unknown journey {j}")
    for r in load(pack, "regulations.json", []):
        for q in r["requirements"]:
            for c in q.get("caps", []):
                if c not in ids: errs.append(f"{q['id']} unknown capability {c}")
            if q.get("deadline") and q["deadline"] not in r.get("dates", {}):
                warn.append(f"{q['id']} deadline key {q['deadline']} not in dates")
    n2, n3 = len(l2), sum(len(v) for v in l3.values())
    print(f"{pack}: {len([c for c in caps if not c.get('parent')])} L1, {n2} L2, {n3} L3, {len(roles)} roles, {len(js)} journeys, "
          f"{len(load(pack, 'processes.json', []))} processes, {len(load(pack, 'regulations.json', []))} regulations, {len(load(pack, 'glossary.json', []))} glossary terms")
    for e in errs: print("  ERROR", e)
    for x in warn: print("  warning", x)
    return not errs


def new_workspace(a):
    ws = os.path.abspath(a.out)
    m = os.path.join(ws, "model")
    if os.path.exists(os.path.join(m, "organisation.json")):
        sys.exit(f"{m} already has a model; refusing to overwrite")
    for d in ["model", "config", "sources", "repository", "output/archive", "processed"] + [f"inbox/{x}" for x in
              ["applications", "procurement", "licences", "roles_raci", "processes", "capabilities", "interfaces", "resilience", "strategy", "regulation", "scenarios", "change_backlog", "archimate"]]:
        os.makedirs(os.path.join(ws, d), exist_ok=True)
    pack = a.pack
    W = lambda n, o: json.dump(o, open(os.path.join(m, n + ".json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    today = dt.date.today().isoformat()
    short = a.short or a.name
    W("organisation", dict(name=a.name, short_name=short, pack=pack, as_of=today, seed=42, cost_scale=1.0, currency={"symbol": "€", "code": "EUR"},
                           context=[], sources={}, data_centres=[], dc_model="active-passive", hosting={}, customer_role="R01",
                           owners_by_category={}, tech_owners_by_category={}, default_business_owner="", default_tech_owner="", licence_metric_by_category={}))
    caps = load(pack, "capabilities.json", [])
    for c in caps:
        c["source"] = "Illustrative (" + pack + " pack)"
    W("capabilities", caps)
    W("capabilities_l3", {k: [dict(x, apps=[]) for x in v] for k, v in load(pack, "capabilities_l3.json", {}).items()})
    W("roles", load(pack, "roles.json", []))
    W("value_streams", load(pack, "value_streams.json", {"customer_value_streams": [], "journeys": []}))
    W("processes", load(pack, "processes.json", []))
    regs = load(pack, "regulations.json", [])
    for r in regs:
        for q in r["requirements"]:
            q.setdefault("apps", []); q.setdefault("procs", [])
    W("regulations", regs)
    for n, o in [("applications", []), ("suppliers", []), ("interfaces", []), ("data_domains", []), ("scenarios", []), ("glossary", []),
                 ("change_portfolio", {"epics": [], "features": []}), ("strategy", {"theme": "", "pillars": [], "initiatives": []})]:
        W(n, o)
    W("versioning", dict(version="1.0", release_date=today, history=[dict(version="1.0", date=today, title="Initial atlas", summary="First build.", source="EA analysis", changes=[])]))
    open(os.path.join(ws, "changelog.md"), "w").write(f"# {short} atlas change log\n")
    print("Workspace created at", ws)
    print("Next: complete model/organisation.json, add applications, suppliers and interfaces (or import an ArchiMate model), map L3 capabilities and journey steps to applications, then run engine/build.py")


ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="cmd")
sub.add_parser("list")
v = sub.add_parser("validate"); v.add_argument("packs", nargs="*")
n = sub.add_parser("new-workspace"); n.add_argument("--pack", required=True); n.add_argument("--name", required=True); n.add_argument("--short", default=""); n.add_argument("--out", required=True)
a = ap.parse_args()
if a.cmd == "list":
    for p in sorted(os.listdir(PACKS)):
        pr = load(p, "profile.json", {})
        print(f"{p:12} {pr.get('name', '')}  ({(pr.get('capability_standard') or {}).get('name', '')})")
elif a.cmd == "validate":
    ok = all(validate(p) for p in (a.packs or sorted(os.listdir(PACKS))))
    sys.exit(0 if ok else 1)
elif a.cmd == "new-workspace":
    new_workspace(a)
else:
    ap.print_help()
