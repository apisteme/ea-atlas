#!/usr/bin/env python3
"""Builds the GitHub Copilot kit (VS Code agent mode and Copilot CLI) from this repository.

    python3 tools/make_github_copilot_kit.py [--out dist/github-copilot]

Writes enterprise-architecture-atlas-github-copilot.zip. Unzip it at the root of the repository that will hold the atlas:

  .github/skills/enterprise-architecture-atlas/   the skill: SKILL.md, engine, importers, packs, reference, ArchiSurance sample
  .github/prompts/atlas-*.prompt.md               /atlas-build, /atlas-refresh, /atlas-what-if, /atlas-example
  .github/instructions/ea-atlas.instructions.md   rules applied to files under ea-atlas/
  EA-ATLAS.md                                     setup guide

The kit is checked, then the ArchiSurance example is built from the staged copy to prove it runs.
"""
import argparse, os, re, shutil, subprocess, sys, tempfile, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "plugins", "enterprise-architecture-atlas", "skills", "enterprise-architecture-atlas")
KIT = os.path.join(ROOT, "kits", "github-copilot")
NAME = "enterprise-architecture-atlas"

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(ROOT, "dist", "github-copilot"))
a = ap.parse_args()
OUT = os.path.abspath(a.out)
stage = os.path.join(OUT, "kit")
shutil.rmtree(stage, ignore_errors=True)
sk = os.path.join(stage, ".github", "skills", NAME)
ign = shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules", "output")

os.makedirs(sk)
shutil.copy(os.path.join(KIT, "SKILL.md"), os.path.join(sk, "SKILL.md"))
for d in ("engine", "importers", "packs"):
    shutil.copytree(os.path.join(SKILL, d), os.path.join(sk, d), ignore=ign)
shutil.copytree(os.path.join(SKILL, "samples"), os.path.join(sk, "samples"), ignore=ign)
# This host runs scripts from a Git repository and calls the assistant Copilot.
p = os.path.join(sk, "engine", "build_dashboard.py")
t = open(p, encoding="utf-8").read()
assert 'ASSISTANT = "Claude"' in t and 'HOST = "workspace"' in t
open(p, "w", encoding="utf-8").write(t.replace('ASSISTANT = "Claude"', 'ASSISTANT = "Copilot"').replace('HOST = "workspace"', 'HOST = "repo"'))
# references, without Claude artifact and skill details
os.makedirs(os.path.join(sk, "reference"))
for f in ("model-schema.md", "pack-authoring.md", "outputs.md"):
    t = open(os.path.join(SKILL, "reference", f), encoding="utf-8").read()
    if f == "outputs.md":
        t = re.sub(r"One self-contained HTML page: .*?\n", "One self-contained HTML page: `output/<prefix>_EA_Dashboard.html`. It works offline and can be shared as a file or published on an internal site. `repository/atlas_page.html` is the same page without its document wrapper.\n", t, count=1)
        t = t.replace("Saved scenarios use the artifact `db` capability with `user` for authorship, falling back to browser storage.", "Saved scenarios are kept in the viewer's browser storage.")
        t = t.replace("saved features use the `features` db collection (browser storage in the standalone file)", "saved features are kept in the viewer's browser storage")
        t = re.sub(r"Recalculate with the xlsx skill's `recalc.py` \(pass it to `build.py --recalc`\) and check for zero formula errors\.",
                   "Excel recalculates every formula when the file is opened; with LibreOffice installed, pass a recalc script to `build.py --recalc`.", t)
        t = re.sub(r"\n## Copilot kit \(optional\).*?(?=\n## )", "\n", t, flags=re.S)
        t = re.sub(r"\n## Prompt file.*\Z", "\n", t, flags=re.S)
    open(os.path.join(sk, "reference", f), "w", encoding="utf-8").write(t)
notice = open(os.path.join(ROOT, "NOTICE.md"), encoding="utf-8").read()
lic = open(os.path.join(ROOT, "LICENSE"), encoding="utf-8").read()
open(os.path.join(sk, "LICENSE.md"), "w", encoding="utf-8").write("# Licence\n\n```\n" + lic + "```\n\n" + notice)
for sub in ("prompts", "instructions"):
    shutil.copytree(os.path.join(KIT, sub), os.path.join(stage, ".github", sub))
shutil.copy(os.path.join(KIT, "README.md"), os.path.join(stage, "EA-ATLAS.md"))

# ---------------------------------------------------------------- checks
problems, files = [], []
for d, _, fs in os.walk(stage):
    for f in fs:
        rel = os.path.relpath(os.path.join(d, f), stage)
        files.append(rel)
        if rel.endswith((".md", ".py", ".js", ".html", ".json")):
            t = open(os.path.join(stage, rel), encoding="utf-8", errors="ignore").read()
            if re.search(r"(?i)\bptsb\b|permanent tsb|bawag|kyndryl", t):
                problems.append(f"client reference in {rel}")
            if rel.endswith((".md", ".json")) and ("—" in t or "–" in t):
                problems.append(f"em or en dash in {rel}")
txt = open(os.path.join(sk, "SKILL.md"), encoding="utf-8").read()
m = re.match(r'^---\nname: ([a-z0-9-]+)\ndescription: "(.*?)"\n', txt)
if not m or m.group(1) != NAME:
    problems.append("SKILL.md name missing or not the folder name")
elif not 1 <= len(m.group(2)) <= 1024:
    problems.append("description longer than 1024 characters")
if re.search(r"(?i)claude|artifact", txt):
    problems.append("SKILL.md mentions Claude-specific features")
for f in os.listdir(os.path.join(stage, ".github", "prompts")):
    if not f.endswith(".prompt.md"):
        problems.append(f"prompt file name: {f}")

# ---------------------------------------------------------------- run the example from the staged kit
tmp = tempfile.mkdtemp()
ws = os.path.join(tmp, "ea-atlas-example")
shutil.copytree(os.path.join(sk, "samples", "archisurance"), ws)
r = subprocess.run([sys.executable, os.path.join(sk, "engine", "build.py"), "--workspace", ws, "--engine", "python"], capture_output=True, text=True)
if r.returncode or "Dash check: clean" not in r.stdout:
    problems.append("example build failed: " + (r.stdout + r.stderr)[-1500:])
shutil.rmtree(tmp, ignore_errors=True)
for d, _, fs in os.walk(stage):
    if os.path.basename(d) == "__pycache__":
        shutil.rmtree(d)
files = [f for f in files if "__pycache__" not in f]

z = os.path.join(OUT, f"{NAME}-github-copilot.zip")
with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
    for rel in sorted(files):
        zf.write(os.path.join(stage, rel), rel.replace(os.sep, "/"))
print(f"Staged {len(files)} files in {stage}")
print(f"{z}  {os.path.getsize(z) // 1024} KB")
print("Checks:", "all passed" if not problems else "")
for p in problems:
    print("  PROBLEM", p)
sys.exit(1 if problems else 0)
