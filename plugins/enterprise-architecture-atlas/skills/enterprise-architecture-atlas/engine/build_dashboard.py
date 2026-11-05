"""Builds the dashboard from the template, the UI modules and repository/data.json.
    python3 build_dashboard.py --workspace path/to/ea-atlas [--assistant NAME] [--host workspace|chat]
Writes output/<prefix>_EA_Dashboard.html (standalone, works offline) and repository/atlas_page.html (the page to publish)."""
import os, json, argparse, html
E = os.path.dirname(os.path.abspath(__file__))
ASSISTANT = "Claude"   # name used in the dashboard's How to update view
HOST = "workspace"     # "workspace": files in an inbox folder; "repo": the same in a Git repository; "chat": files attached in a chat, atlas kept as one file


def _rd(f):
    return open(os.path.join(E, f), encoding="utf-8").read()


def page_template():
    """The dashboard page with its scripts inlined. Built from dashboard_template.html and the .js modules when
    they are present; otherwise read from dashboard_page.py, the same page stored as a Python string for hosts
    that do not accept .js or .html files (tools/make_copilot_skill.py writes it)."""
    if not os.path.exists(os.path.join(E, "dashboard_template.html")):
        import sys
        sys.path.insert(0, E)
        from dashboard_page import TEMPLATE
        return TEMPLATE
    t = _rd("dashboard_template.html")
    t = t.replace("/*__ENGINE__*/", _rd("scenario_engine.js").replace("if (typeof module!=='undefined') module.exports = ScenarioEngine;", ""))
    t = t.replace("/*__STRATEGY_UI__*/", _rd("strategy_ui.js"))
    t = t.replace("/*__SCENARIOS_UI__*/", _rd("scenarios_ui.js"))
    t = t.replace("/*__GUIDE_UI__*/", _rd("guide_ui.js"))
    t = t.replace("/*__FEATURE_ENGINE__*/", _rd("feature_engine.js").replace("if (typeof module!=='undefined') module.exports = FeatureImpact;", ""))
    t = t.replace("/*__FEATURES_UI__*/", _rd("features_ui.js"))
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--assistant", default=os.environ.get("ATLAS_ASSISTANT", ASSISTANT))
    ap.add_argument("--host", default=os.environ.get("ATLAS_HOST", HOST), choices=["workspace", "chat", "repo"])
    args = ap.parse_args()
    WS = os.path.abspath(args.workspace)
    REPO, OUT = os.path.join(WS, "repository"), os.path.join(WS, "output")
    os.makedirs(OUT, exist_ok=True)
    d = json.load(open(os.path.join(REPO, "data.json"), encoding="utf-8"))
    d["meta"]["assistant"], d["meta"]["host"] = args.assistant, args.host
    t = page_template().replace("__TITLE__", html.escape(d["meta"].get("dashboard_title", "Architecture Atlas")))
    s = json.dumps(d, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    b = t.replace("__DATA__", s)
    page = os.path.join(REPO, "atlas_page.html")
    open(page, "w", encoding="utf-8").write(b)
    prefix = d["meta"].get("file_prefix", "Atlas")
    sa = os.path.join(OUT, f"{prefix}_EA_Dashboard.html")
    open(sa, "w", encoding="utf-8").write('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n<style>[hidden]{display:none!important}body{margin:0}</style>\n'
                                          + b.replace('<div class="app">', '</head><body>\n<div class="app">', 1) + '\n</body></html>')
    print("page", page)
    print("standalone", sa)
    print("dashes", b.count("—"), b.count("–"), "size", len(b) // 1024, "KB")


if __name__ == "__main__":
    main()
