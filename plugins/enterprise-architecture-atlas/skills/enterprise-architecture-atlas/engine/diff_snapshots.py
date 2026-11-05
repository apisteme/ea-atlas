"""Field-level diff between two atlas snapshots (data.json). Used by build_data.py and on its own:
    python3 diff_snapshots.py versions/v1.14.json data.json"""
import json, sys

# collection, key field, label field, fields to ignore (derived or illustrative noise)
SPECS = [
 ("apps", "id", "name", {"tier_n"}),
 ("suppliers", "id", "name", set()),
 ("capabilities", "id", "name", {"strategic_initiatives"}),
 ("capabilities_l3", "id", "name", set()),
 ("epics", "id", "name", set()),
 ("features", "id", "name", set()),
 ("roles", "id", "name", set()),
 ("customer_value_streams", "id", "name", set()),
 ("value_streams", "id", "name", set()),
 ("steps", "id", "name", set()),
 ("business_processes", "id", "name", set()),
 ("interfaces", "id", "data", set()),
 ("data_domains", "id", "name", set()),
 ("data_centres", "id", "name", set()),
 ("contracts", "id", "title", set()),
 ("licences", "app", "app", set()),
 ("support", "app", "app", set()),
 ("resilience", "app", "app", set()),
]
TYPE_LABEL = {"apps":"Application","suppliers":"Supplier","capabilities":"Capability","capabilities_l3":"Capability L3","epics":"Epic","features":"Feature","roles":"Role","customer_value_streams":"Value stream",
  "value_streams":"Journey","steps":"Process step","business_processes":"Business process","interfaces":"Interface","data_domains":"Data domain",
  "data_centres":"Data centre","contracts":"Contract","licences":"Licence","support":"Support agreement","resilience":"Resilience","initiatives":"Strategic initiative","requirements":"Regulatory requirement"}

def _fmt(v):
    if isinstance(v, list): return "; ".join(_fmt(x) for x in v) if v else "(none)"
    if isinstance(v, dict): return ", ".join(f"{k} {_fmt(x)}" for k, x in v.items())
    if v is None or v == "": return "(blank)"
    return str(v)

def _collections(d):
    out = {}
    for name, key, label, ign in SPECS:
        out[name] = (key, label, ign, {x[key]: x for x in d.get(name, [])})
    out["initiatives"] = ("id", "title", set(), {x["id"]: x for x in d.get("strategy", {}).get("initiatives", [])})
    out["requirements"] = ("id", "short", set(), {q["id"]: q for r in d.get("regulations", []) for q in r["requirements"]})
    return out

def diff(old, new):
    O, N = _collections(old), _collections(new)
    apps = {a["id"]: a["name"] for a in new.get("apps", [])}
    apps.update({a["id"]: a["name"] for a in old.get("apps", []) if a["id"] not in apps})
    changes = []
    for name in N:
        key, label, ign, nx = N[name]; ox = O.get(name, (key, label, ign, {}))[3]
        lab = lambda x: (apps.get(x[label], x[label]) if label == "app" else x.get(label, ""))
        for k in nx.keys() - ox.keys():
            changes.append(dict(type=TYPE_LABEL[name], id=k, name=lab(nx[k]), action="Added", field="", old="", new=""))
        for k in ox.keys() - nx.keys():
            changes.append(dict(type=TYPE_LABEL[name], id=k, name=lab(ox[k]), action="Removed", field="", old="", new=""))
        for k in nx.keys() & ox.keys():
            a, b = ox[k], nx[k]
            for f in sorted(set(a) | set(b)):
                if f in ign or f.startswith("__"): continue
                if a.get(f) != b.get(f) and (a.get(f) or b.get(f)):
                    changes.append(dict(type=TYPE_LABEL[name], id=k, name=lab(b), action="Updated", field=f, old=_fmt(a.get(f)), new=_fmt(b.get(f))))
    order = {"Added": 0, "Updated": 1, "Removed": 2}
    changes.sort(key=lambda c: (c["type"], order[c["action"]], c["id"], c["field"]))
    return changes

def summarise(changes):
    s = {}
    for c in changes:
        s.setdefault(c["type"], {"Added": 0, "Updated": 0, "Removed": 0})
        if c["action"] == "Updated":
            continue
        s[c["type"]][c["action"]] += 1
    upd = {}
    for c in changes:
        if c["action"] == "Updated": upd.setdefault(c["type"], set()).add(c["id"])
    for t, ids in upd.items(): s.setdefault(t, {"Added": 0, "Updated": 0, "Removed": 0})["Updated"] = len(ids)
    return s

if __name__ == "__main__":
    o, n = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
    ch = diff(o, n)
    for t, c in sorted(summarise(ch).items()): print(f"{t}: {c['Added']} added, {c['Updated']} updated, {c['Removed']} removed")
    for c in ch[:200]: print(f"  {c['action']:8} {c['type']:22} {c['id']:8} {c['name'][:40]:40} {c['field']}: {c['old'][:40]} -> {c['new'][:40]}" if c['field'] else f"  {c['action']:8} {c['type']:22} {c['id']:8} {c['name']}")
