#!/usr/bin/env python3
"""Runs the whole atlas build for one workspace, in order, and stops at the first failure.

    python3 build.py --workspace path/to/ea-atlas [--skip-xlsx] [--recalc path/to/recalc.py] [--engine auto|node|python]

1. build_data.py       model/*.json + industry pack -> repository/data.json (with snapshot and diff)
2. impact engines      example scenarios and change backlog for the Excel: compute_scenarios.js with Node,
                       or impact_engine.py (same results) when Node is not available
3. build_xlsx.py       Excel repository (openpyxl if installed, otherwise the built-in writer),
                       then recalculated if a recalc script is given
4. build_dashboard.py  publishable page and standalone HTML
5. checks              validation errors, dashes

Only the Python standard library is required. Node, openpyxl and LibreOffice are used when present.
"""
import os, sys, json, subprocess, argparse, shutil
E = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--workspace", default=".")
ap.add_argument("--skip-xlsx", action="store_true")
ap.add_argument("--recalc", default="", help="path to a LibreOffice recalc script (for example the xlsx skill's recalc.py)")
ap.add_argument("--engine", default="auto", choices=["auto", "node", "python"])
a = ap.parse_args()
WS = os.path.abspath(a.workspace)


def run(cmd):
    print("$", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=E)
    if r.returncode:
        sys.exit(f"Step failed: {' '.join(cmd)}")


run([sys.executable, "build_data.py", "--workspace", WS])
d = json.load(open(os.path.join(WS, "repository", "data.json"), encoding="utf-8"))
errs = d["meta"]["validation"]["errors"]
if errs:
    print("\nValidation errors (fix the model, then rebuild):")
    for e in errs:
        print("  -", e)
    sys.exit(1)
node = shutil.which("node")
if os.path.exists(os.path.join(E, "compute_scenarios.js")) and (a.engine == "node" or (a.engine == "auto" and node)):
    run([node or "node", "compute_scenarios.js", WS])
else:
    run([sys.executable, "impact_engine.py", "--workspace", WS])
if not a.skip_xlsx:
    run([sys.executable, "build_xlsx.py", "--workspace", WS])
    if a.recalc:
        x = os.path.join(WS, "output", f"{d['meta']['file_prefix']}_EA_Repository.xlsx")
        run([sys.executable, a.recalc, x])
run([sys.executable, "build_dashboard.py", "--workspace", WS])
bad = []
for root, _, files in os.walk(os.path.join(WS, "output")):
    for f in files:
        if f.endswith((".html", ".md", ".json")):
            t = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
            if "—" in t or "–" in t:
                bad.append(f)
print("\nDash check:", "clean" if not bad else "em or en dashes in " + ", ".join(bad))
print("Outputs:")
for f in sorted(os.listdir(os.path.join(WS, "output"))):
    p = os.path.join(WS, "output", f)
    if os.path.isfile(p):
        print(f"  {p}  ({os.path.getsize(p) // 1024} KB)")
print("Done. Version", d["meta"]["version"])
