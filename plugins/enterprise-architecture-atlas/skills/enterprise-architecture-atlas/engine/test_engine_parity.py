#!/usr/bin/env python3
"""Checks that impact_engine.py gives exactly the same results as scenario_engine.js and feature_engine.js.
Needs Node. Run it after changing either engine.

    python3 test_engine_parity.py --workspace path/to/ea-atlas [--cases 400]

Generates scenarios of every type against every application, platform, supplier, data centre and regulation,
every feature and epic in the backlog, and random feature variants, runs them through both engines, and
compares the full result objects.
"""
import argparse, json, os, random, subprocess, sys, tempfile
E = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, E)
import impact_engine as PY

ap = argparse.ArgumentParser()
ap.add_argument("--workspace", required=True)
ap.add_argument("--cases", type=int, default=400)
a = ap.parse_args()
D = json.load(open(os.path.join(os.path.abspath(a.workspace), "repository", "data.json"), encoding="utf-8"))
rnd = random.Random(1)

sc = []
for x in D["apps"]:
    sc.append(dict(type="app_outage", targets=[x["id"]]))
    sc.append(dict(type="decommission", targets=[x["id"]]))
    if x.get("platform"):
        sc.append(dict(type="platform_failure", targets=[x["id"]]))
for s in D["suppliers"]:
    sc.append(dict(type="supplier_failure", targets=[s["id"]]))
    sc.append(dict(type="price_change", targets=[s["id"]], pct=rnd.choice([5, 10, 15, 37.5, -20])))
dcs = [d["id"] for d in D["data_centres"]]
for d in dcs:
    sc.append(dict(type="dc_loss", targets=[d]))
if len(dcs) > 1:
    sc.append(dict(type="dc_loss", targets=dcs[:2]))
for r in D["regulations"]:
    sc.append(dict(type="regulatory_change", regulation=r["id"], targets=[]))
    qs = [q["id"] for q in r["requirements"]]
    if qs:
        sc.append(dict(type="regulatory_change", regulation=r["id"], targets=rnd.sample(qs, max(1, len(qs) // 2))))
ids = [x["id"] for x in D["apps"]]
for _ in range(a.cases // 4):
    t = rnd.choice(["app_outage", "decommission", "supplier_failure", "price_change"])
    pool = ids if t in ("app_outage", "decommission") else [s["id"] for s in D["suppliers"]]
    sc.append(dict(type=t, targets=rnd.sample(pool, rnd.randint(1, min(4, len(pool)))), pct=rnd.choice([10, 25])))

ft = list(D["features"])
l3 = [c["id"] for c in D["capabilities_l3"]]
st = [s["id"] for s in D["steps"]]
drv = [i["id"] for i in D["strategy"]["initiatives"]] + [q["id"] for r in D["regulations"] for q in r["requirements"]] + [b["id"] for b in (D.get("programme") or {}).get("decisions", [])]
types = ["New", "Enhance", "Configure", "Integrate", "Replace", "Retire"]
for k in range(a.cases):
    f = dict(id=f"T{k}", epic="", name=f"Test {k}", status=rnd.choice(["Idea", "Ready", "Done"]), target=f"{rnd.choice([2026, 2027, 2028])}-Q{rnd.randint(1, 4)}",
             apps={x: rnd.choice(types) for x in rnd.sample(ids, rnd.randint(1, min(5, len(ids))))},
             caps=rnd.sample(l3, min(len(l3), rnd.randint(0, 3))), steps=rnd.sample(st, min(len(st), rnd.randint(0, 3))),
             new_ifs=[dict(source=rnd.choice(ids), target=rnd.choice(ids), data="x")] if rnd.random() < 0.3 else [],
             drivers=rnd.sample(drv, min(len(drv), rnd.randint(0, 3))), depends=rnd.sample([x["id"] for x in D["features"]], min(len(D["features"]), rnd.randint(0, 2))))
    ft.append(f)
cases = dict(scenarios=sc, features=ft)

harness = r"""
const fs=require('fs'), path=require('path'); const E=process.argv[2];
const S=require(path.join(E,'scenario_engine.js')), F=require(path.join(E,'feature_engine.js'));
const D=JSON.parse(fs.readFileSync(process.argv[3],'utf8')), C=JSON.parse(fs.readFileSync(process.argv[4],'utf8'));
const out={scenarios:C.scenarios.map(sc=>S.run(D,sc)), features:C.features.map(f=>F.run(D,f,C.features.concat(D.features))), epics:D.epics.map(e=>F.epic(D,e,D.features))};
fs.writeFileSync(process.argv[5], JSON.stringify(out));
"""
tmp = tempfile.mkdtemp()
P = lambda n: os.path.join(tmp, n)
open(P("h.js"), "w").write(harness)
json.dump(cases, open(P("cases.json"), "w"))
r = subprocess.run(["node", P("h.js"), E, os.path.join(os.path.abspath(a.workspace), "repository", "data.json"), P("cases.json"), P("js.json")], capture_output=True, text=True)
if r.returncode:
    sys.exit(r.stderr)
JS = json.load(open(P("js.json")))
D2 = json.load(open(os.path.join(os.path.abspath(a.workspace), "repository", "data.json"), encoding="utf-8"))
PYR = dict(scenarios=[PY.run_scenario(D2, s) for s in sc], features=[PY.run_feature(D2, f, ft + D2["features"]) for f in ft], epics=[PY.run_epic(D2, e, D2["features"]) for e in D2["epics"]])
PYR = json.loads(json.dumps(PYR))


def diff(x, y, p=""):
    if isinstance(x, dict) and isinstance(y, dict):
        if list(x.keys()) != list(y.keys()) and set(x.keys()) != set(y.keys()):
            return [f"{p}: keys {sorted(set(x) ^ set(y))}"]
        if list(x.keys()) != list(y.keys()):
            return [f"{p}: key order differs"]
        out = []
        for k in x:
            out += diff(x[k], y[k], f"{p}.{k}")
        return out
    if isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y):
            return [f"{p}: length {len(x)} vs {len(y)}"]
        out = []
        for i, (u, v) in enumerate(zip(x, y)):
            out += diff(u, v, f"{p}[{i}]")
        return out
    if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) and not isinstance(y, bool):
        return [] if abs(x - y) < 1e-9 else [f"{p}: {x} vs {y}"]
    return [] if x == y else [f"{p}: {x!r} vs {y!r}"]


errs = diff(JS, PYR)
print(f"compared {len(sc)} scenarios, {len(ft)} features, {len(D['epics'])} epics: {len(errs)} differences")
for e in errs[:20]:
    print("  ", e)
sys.exit(1 if errs else 0)
