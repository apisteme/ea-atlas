#!/usr/bin/env python3
"""Keep a whole atlas in one file, for hosts where the working folder does not survive between sessions
(Copilot Studio, Agent Builder, chat assistants). The user keeps the bundle and uploads it next time.

    python3 atlas_bundle.py pack   --workspace ea-atlas [--out MyOrg_atlas_model.json]
    python3 atlas_bundle.py unpack MyOrg_atlas_model.json --workspace ea-atlas
    python3 atlas_bundle.py unpack MyOrg_atlas_workspace.zip --workspace ea-atlas

The bundle holds the model files, the change log, source links and the snapshot of the current release
(so the next release can be compared with it). It does not hold outputs: rebuild them with build.py.
"""
import argparse, datetime as dt, json, os, re, sys, zipfile

FORMAT = "ea-atlas-bundle"
INBOX = ["applications", "procurement", "licences", "roles_raci", "processes", "capabilities", "interfaces", "resilience",
         "strategy", "regulation", "scenarios", "change_backlog", "archimate"]


def vt(v):
    return tuple(int(x) for x in v.split("."))


def pack(ws, out):
    m = os.path.join(ws, "model")
    if not os.path.exists(os.path.join(m, "organisation.json")):
        sys.exit(f"No model in {ws}")
    model = {}
    for f in sorted(os.listdir(m)):
        if f.endswith(".json"):
            model[f] = json.load(open(os.path.join(m, f), encoding="utf-8"))
    imp = os.path.join(m, "_import", "id_map.json")
    org = model["organisation.json"]
    ver = model.get("versioning.json", {}).get("version", "1.0")
    vdir = os.path.join(ws, "repository", "versions")
    snap = None
    if os.path.isdir(vdir):
        vs = sorted([f[1:-5] for f in os.listdir(vdir) if re.match(r"^v[\d.]+\.json$", f)], key=vt)
        keep = [v for v in vs if vt(v) <= vt(ver)]
        if keep:
            snap = dict(version=keep[-1], data=json.load(open(os.path.join(vdir, f"v{keep[-1]}.json"), encoding="utf-8")))
    rd = lambda p: open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    b = dict(format=FORMAT, bundle_version=1, created=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
             organisation=org.get("name"), short_name=org.get("short_name"), pack=org.get("pack"), version=ver,
             model=model, archimate_id_map=json.load(open(imp, encoding="utf-8")) if os.path.exists(imp) else None,
             changelog_md=rd(os.path.join(ws, "changelog.md")), links_md=rd(os.path.join(ws, "sources", "links.md")), snapshot=snap)
    prefix = org.get("file_prefix") or re.sub(r"[^A-Za-z0-9]+", "_", org.get("short_name") or org["name"]).strip("_")
    out = out or os.path.join(ws, "output", f"{prefix}_atlas_model.json")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(b, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"Bundle written: {out} ({os.path.getsize(out) // 1024} KB), {org.get('short_name') or org['name']} v{ver}, {len(model)} model files"
          + (f", snapshot v{snap['version']}" if snap else ", no snapshot yet"))


def _safe(name):
    n = os.path.normpath(name)
    if n.startswith("..") or os.path.isabs(n):
        raise ValueError(f"unsafe path in archive: {name}")
    return n


def unpack(src, ws):
    ws = os.path.abspath(ws)
    m = os.path.join(ws, "model")
    if os.path.exists(os.path.join(m, "organisation.json")):
        sys.exit(f"{m} already holds a model; unpack into an empty workspace")
    for d in ["model", "repository/versions", "output/archive", "sources", "processed"] + [f"inbox/{x}" for x in INBOX]:
        os.makedirs(os.path.join(ws, d), exist_ok=True)
    if src.lower().endswith(".zip"):
        with zipfile.ZipFile(src) as z:
            names = z.namelist()
            roots = {n.split("/")[0] for n in names if "/model/organisation.json" in n or n.startswith("model/organisation.json")}
            base = "" if any(n.startswith("model/organisation.json") for n in names) else (sorted(roots)[0] + "/" if roots else None)
            if base is None:
                sys.exit("The zip has no model/organisation.json")
            for n in names:
                if n.endswith("/") or not n.startswith(base):
                    continue
                rel = _safe(n[len(base):])
                if not rel.split(os.sep)[0] in ("model", "repository", "sources", "changelog.md", "config"):
                    continue
                if rel.startswith("repository") and not rel.startswith(os.path.join("repository", "versions")):
                    continue
                p = os.path.join(ws, rel)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with z.open(n) as fi, open(p, "wb") as fo:
                    fo.write(fi.read())
        print(f"Workspace unpacked from zip into {ws}")
        return
    b = json.load(open(src, encoding="utf-8"))
    if b.get("format") != FORMAT:
        sys.exit("Not an atlas bundle (format field missing)")
    for f, content in b["model"].items():
        json.dump(content, open(os.path.join(m, _safe(f)), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if b.get("archimate_id_map"):
        os.makedirs(os.path.join(m, "_import"), exist_ok=True)
        json.dump(b["archimate_id_map"], open(os.path.join(m, "_import", "id_map.json"), "w"), indent=1)
    if b.get("snapshot"):
        s = b["snapshot"]
        json.dump(s["data"], open(os.path.join(ws, "repository", "versions", f"v{s['version']}.json"), "w", encoding="utf-8"), separators=(",", ":"))
    open(os.path.join(ws, "changelog.md"), "w", encoding="utf-8").write(b.get("changelog_md") or "")
    open(os.path.join(ws, "sources", "links.md"), "w", encoding="utf-8").write(b.get("links_md") or "")
    print(f"Unpacked {b.get('short_name') or b.get('organisation')} v{b.get('version')} ({b.get('pack')} pack) into {ws}"
          + (f"; previous release snapshot v{b['snapshot']['version']} restored" if b.get("snapshot") else ""))


ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="cmd")
p = sub.add_parser("pack"); p.add_argument("--workspace", required=True); p.add_argument("--out", default="")
u = sub.add_parser("unpack"); u.add_argument("bundle"); u.add_argument("--workspace", required=True)
a = ap.parse_args()
if a.cmd == "pack":
    pack(os.path.abspath(a.workspace), a.out)
elif a.cmd == "unpack":
    unpack(a.bundle, a.workspace)
else:
    ap.print_help()
