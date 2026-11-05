#!/usr/bin/env python3
"""Reports what this host can run, so the agent knows which build path to use. Standard library only.

    python3 check_env.py
"""
import os, platform, shutil, subprocess, sys, tempfile

E = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(E)
print("Skill folder:", SKILL)
print("Scripts folder:", E)
packs = os.path.join(SKILL, "packs")
print("Industry packs:", ", ".join(sorted(os.listdir(packs))) if os.path.isdir(packs) else "NOT FOUND")
print("Python:", platform.python_version(), sys.executable)
try:
    import openpyxl
    print("openpyxl:", openpyxl.__version__, "(styled Excel)")
except ImportError:
    print("openpyxl: not installed (Excel uses the built-in writer: same tabs and formulas, plain formatting)")
node = shutil.which("node")
if node:
    try:
        v = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        v = "?"
    print("Node:", v, node, "(JavaScript engines)")
else:
    print("Node: not available (impact_engine.py gives the same results)")
print("LibreOffice:", shutil.which("soffice") or "not available (Excel recalculates formulas when opened)")
try:
    d = tempfile.mkdtemp()
    open(os.path.join(d, "t.txt"), "w").write("ok")
    print("Writable temp folder:", d)
except Exception as e:
    print("Writable temp folder: NO", e)
print("Working folder:", os.getcwd(), "(writable)" if os.access(os.getcwd(), os.W_OK) else "(read-only: use the temp folder for the workspace)")
print("Result: ready to build" if os.path.isdir(packs) else "Result: skill files missing")
