#!/usr/bin/env python3
"""Import an ArchiMate model into a draft atlas model.

    python3 archimate_import.py MODEL.archimate|MODEL.xml --workspace path/to/ea-atlas [--source "Customer-provided"] [--ref URL]

Reads either an Archi model file (.archimate) or an Open Group ArchiMate Model Exchange File (.xml),
and writes:
  model/_import/archimate.json   every element and relationship, normalised (for review and refresh)
  model/_import/id_map.json      ArchiMate id -> atlas id, so a re-import keeps atlas IDs stable
  model/_import/draft/*.json     draft atlas model files: applications, roles, interfaces, data_domains,
                                 journeys (from triggering chains), processes, strategy, platforms
The drafts are a starting point. The assistant then maps them to the industry pack (capabilities, regulations),
fills the gaps with tagged illustrative data, and writes the real model files.

What maps to what
  ApplicationComponent            -> application (A..)
  Node, Device, SystemSoftware    -> platform application (A..), with runs_on links from what they serve or realise
  BusinessActor (internal)        -> organisation unit; BusinessRole and leaf actors -> role (R..)
  BusinessProcess, BusinessInteraction, BusinessEvent with Triggering -> journey steps in order
  Assignment role/actor -> step   -> Responsible role
  Serving app/app service -> step -> application used in the step
  Serving or Flow between apps    -> interface (I..)
  DataObject accessed by an app   -> data domain; the app that writes it is the system of record
  BusinessFunction, Capability    -> capability candidates
  Goal, Outcome, Driver           -> strategic pillars; Principle, CourseOfAction, WorkPackage -> initiatives
"""
import argparse, json, os, re, sys
import xml.etree.ElementTree as ET

XSI = "{http://www.w3.org/2001/XMLSchema-instance}type"


def clean(s):
    return re.sub(r"\s+", " ", (s or "").strip())


def parse_archi(root):
    els, rels = {}, []
    for e in root.iter("element"):
        t = (e.get(XSI) or "").split(":")[-1]
        doc = e.find("documentation")
        props = {p.get("key"): p.get("value") for p in e.findall("property")}
        if t.endswith("Relationship"):
            rels.append(dict(id=e.get("id"), type=t.replace("Relationship", ""), source=e.get("source"), target=e.get("target"), name=clean(e.get("name")), access=e.get("accessType")))
        elif "DiagramModel" in t or t in ("SketchModel", "CanvasModel"):
            continue
        else:
            els[e.get("id")] = dict(id=e.get("id"), type=t, name=clean(e.get("name")), doc=clean(doc.text if doc is not None else ""), props=props)
    return els, rels


def parse_exchange(root):
    ns = {"a": root.tag.split("}")[0].strip("{")}
    els, rels = {}, []
    def txt(node, tag):
        x = node.find(f"a:{tag}", ns)
        return clean(x.text if x is not None else "")
    for e in root.iterfind(".//a:elements/a:element", ns):
        els[e.get("identifier")] = dict(id=e.get("identifier"), type=e.get(XSI), name=txt(e, "name"), doc=txt(e, "documentation"), props={})
    for r in root.iterfind(".//a:relationships/a:relationship", ns):
        rels.append(dict(id=r.get("identifier"), type=r.get(XSI), source=r.get("source"), target=r.get("target"), name=txt(r, "name"), access=r.get("accessType")))
    return els, rels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--source", default="Customer-provided", help="data confidence tag for imported facts")
    ap.add_argument("--ref", default="", help="optional link recorded on imported items")
    a = ap.parse_args()
    root = ET.parse(a.model).getroot()
    els, rels = (parse_exchange(root) if "opengroup" in root.tag else parse_archi(root))
    mname = root.get("name") or os.path.basename(a.model)
    out = os.path.join(os.path.abspath(a.workspace), "model", "_import")
    os.makedirs(os.path.join(out, "draft"), exist_ok=True)
    mp_path = os.path.join(out, "id_map.json")
    idmap = json.load(open(mp_path)) if os.path.exists(mp_path) else {}
    used = set(idmap.values())

    def new_id(prefix, archi_id, width=2):
        if archi_id in idmap:
            return idmap[archi_id]
        n = 1
        while f"{prefix}{n:0{width}d}" in used:
            n += 1
        v = f"{prefix}{n:0{width}d}"
        idmap[archi_id] = v
        used.add(v)
        return v

    src = a.source + f" (ArchiMate model: {mname})"
    of = lambda t: [e for e in els.values() if e["type"] == t]
    by_src = lambda i, types=None: [r for r in rels if r["source"] == i and (types is None or r["type"] in types)]
    by_tgt = lambda i, types=None: [r for r in rels if r["target"] == i and (types is None or r["type"] in types)]

    # applications and platforms
    apps = {}
    for e in of("ApplicationComponent"):
        apps[e["id"]] = dict(id=new_id("A", e["id"]), name=e["name"], product=e["name"], vendor="", category="To classify", capabilities=[],
                             time="Tolerate", tier=2, hosting="To confirm", critical=False, source=src, ref=a.ref, archimate_id=e["id"], description=e["doc"])
    plats = {}
    for t in ("Node", "Device", "SystemSoftware", "TechnologyCollaboration"):
        for e in of(t):
            plats[e["id"]] = dict(id=new_id("A", e["id"]), name=e["name"], product=e["name"], vendor="", category="Infrastructure", capabilities=[], time="Tolerate",
                                  tier=1, hosting="To confirm", critical=False, platform={}, source=src, ref=a.ref, archimate_id=e["id"], archimate_type=t, description=e["doc"])
    # application services and technology services realised by components / platforms
    realiser = {}
    for r in rels:
        if r["type"] == "Realization" and (r["source"] in apps or r["source"] in plats) and r["target"] not in apps and r["target"] not in plats:
            realiser.setdefault(r["target"], []).append(r["source"])
    # runs_on: platform (or tech service it realises) serving an app
    for r in rels:
        if r["type"] in ("Serving", "Realization", "Assignment"):
            s, t = r["source"], r["target"]
            ps = [s] if s in plats else [p for p in realiser.get(s, []) if p in plats]
            for p in ps:
                if t in apps:
                    ro = apps[t].setdefault("runs_on", [])
                    if not any(x["app"] == plats[p]["id"] for x in ro):
                        ro.append(dict(app=plats[p]["id"], status="From ArchiMate model"))
    # interfaces between applications
    def app_of(x):
        if x in apps: return [x]
        return [y for y in realiser.get(x, []) if y in apps]
    ifs, seen = [], set()
    for r in rels:
        if r["type"] not in ("Serving", "Flow", "Triggering"):
            continue
        S, T = app_of(r["source"]), app_of(r["target"])
        for s in S:
            for t in T:
                if s == t or (s, t) in seen:
                    continue
                seen.add((s, t))
                svc = els.get(r["source"], {}).get("name", "") if r["source"] not in apps else ""
                ifs.append(dict(source_app=apps[s]["id"], target_app=apps[t]["id"], data=r["name"] or svc or "To confirm",
                                protocol="To confirm", frequency="To confirm", source=src))
    # roles: business roles and actors (actors with children become org units)
    parent_of = {}
    for r in rels:
        if r["type"] in ("Composition", "Aggregation", "Association") and els.get(r["source"], {}).get("type") == "BusinessActor" and els.get(r["target"], {}).get("type") == "BusinessActor":
            parent_of.setdefault(r["target"], r["source"])
    roles = {}
    for e in of("BusinessRole") + of("BusinessActor") + of("BusinessCollaboration"):
        roles[e["id"]] = dict(id=new_id("R", e["id"]), name=e["name"], unit=els.get(parent_of.get(e["id"], ""), {}).get("name", "To confirm"),
                              family="To classify", source=src, archimate_id=e["id"], archimate_type=e["type"])
    # journeys: chains of triggering relations among behaviour elements
    beh = {e["id"] for e in els.values() if e["type"] in ("BusinessProcess", "BusinessInteraction", "BusinessEvent", "BusinessFunction")}
    nxt = {}
    for r in rels:
        if r["type"] in ("Triggering", "Flow") and r["source"] in beh and r["target"] in beh and els[r["source"]]["type"] != "BusinessFunction":
            nxt.setdefault(r["source"], []).append(r["target"])
    has_in = {t for v in nxt.values() for t in v}
    starts = [e for e in nxt if e not in has_in]
    journeys = []
    for s in starts:
        chain, cur, guard = [], s, 0
        while cur and guard < 50 and cur not in chain:
            chain.append(cur)
            cur = (nxt.get(cur) or [None])[0]
            guard += 1
        trig = els[chain[0]]["name"] if els[chain[0]]["type"] == "BusinessEvent" else ""
        steps = []
        for x in chain:
            if els[x]["type"] == "BusinessEvent":
                continue
            R = [roles[r["source"]]["id"] for r in by_tgt(x, ("Assignment",)) if r["source"] in roles]
            used_apps = []
            for r in by_tgt(x, ("Serving",)):
                used_apps += [apps[y]["id"] for y in app_of(r["source"])]
            steps.append(dict(name=els[x]["name"], archimate_id=x, R=R, A=R[0] if R else "", C=[], I=[], apps=sorted(set(used_apps)), capabilities=[]))
        if steps:
            journeys.append(dict(name=" then ".join(st["name"] for st in steps[:2]) + ("..." if len(steps) > 2 else ""), trigger=trig, steps=steps, source=src))
    # processes, data, capabilities, strategy
    procs = [dict(name=e["name"], archimate_id=e["id"], type=e["type"]) for e in els.values() if e["type"] in ("BusinessProcess", "BusinessInteraction")]
    data = []
    for e in of("DataObject"):
        acc = [r for r in rels if r["type"] == "Access" and r["target"] == e["id"]]
        writers = [apps[s]["id"] for r in acc for s in app_of(r["source"]) if (r.get("access") in ("write", "readwrite", None) or "update" in r["name"] or "crud" in r["name"])]
        readers = [apps[s]["id"] for r in acc for s in app_of(r["source"])]
        data.append(dict(name=e["name"], sor=writers[0] if writers else "", consumers=sorted(set(readers) - set(writers[:1])), source=src, archimate_id=e["id"]))
    caps = [dict(name=e["name"], type=e["type"], archimate_id=e["id"], description=e["doc"]) for e in els.values() if e["type"] in ("BusinessFunction", "Capability")]
    pillars = [dict(name=e["name"], type=e["type"], archimate_id=e["id"], description=e["doc"]) for e in els.values() if e["type"] in ("Goal", "Outcome", "Driver")]
    inits = [dict(name=e["name"], type=e["type"], archimate_id=e["id"], description=e["doc"]) for e in els.values() if e["type"] in ("Principle", "CourseOfAction", "WorkPackage", "Requirement")]
    services = [dict(name=e["name"], type=e["type"], realised_by=[(apps.get(x) or plats.get(x) or {}).get("id") for x in realiser.get(e["id"], [])], archimate_id=e["id"])
                for e in els.values() if e["type"] in ("BusinessService", "ApplicationService", "TechnologyService")]

    W = lambda n, o: json.dump(o, open(os.path.join(out, "draft", n + ".json"), "w"), indent=1, ensure_ascii=False)
    W("applications", list(apps.values()) + list(plats.values()))
    W("roles", list(roles.values()))
    W("interfaces", ifs)
    W("journeys", journeys)
    W("processes", procs)
    W("data_domains", data)
    W("capability_candidates", caps)
    W("strategy_candidates", dict(pillars=pillars, initiatives=inits))
    W("services", services)
    json.dump(dict(model=mname, elements=list(els.values()), relationships=rels), open(os.path.join(out, "archimate.json"), "w"), indent=1, ensure_ascii=False)
    json.dump(idmap, open(mp_path, "w"), indent=1)
    from collections import Counter
    print(f"Imported {mname}: {len(els)} elements, {len(rels)} relationships")
    print("  applications", len(apps), "platforms", len(plats), "roles", len(roles), "interfaces", len(ifs), "journeys", len(journeys),
          "data objects", len(data), "capability candidates", len(caps), "goals", len(pillars), "principles", len(inits))
    print("  element types:", dict(Counter(e["type"] for e in els.values()).most_common(12)))
    print("Drafts written to", os.path.join(out, "draft"))


if __name__ == "__main__":
    main()
