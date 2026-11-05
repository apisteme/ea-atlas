#!/usr/bin/env python3
"""Builds the GitHub Pages site into docs/ from this repository.

    python3 tools/build_site.py [--repo owner/name] [--no-shots]

1. Builds the three kits (Claude skill zip, Copilot Studio zips, GitHub Copilot kit) into docs/downloads/.
2. Builds every example listed in site/examples.json from its sample model and stores the dashboard, Excel,
   atlas file and source model in docs/examples/<id>/.
3. Takes screenshots of the example dashboards with Playwright when it is installed (otherwise keeps any existing ones).
4. Writes the home page, the examples gallery, one page per example and the three setup guides.

Pages are served from docs/ on the default branch. Only the Python standard library is required, plus the markdown
package for the guides.
"""
import argparse, html, json, os, re, shutil, subprocess, sys, tempfile, zipfile
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "plugins", "enterprise-architecture-atlas", "skills", "enterprise-architecture-atlas")
SITE, DOCS = os.path.join(ROOT, "site"), os.path.join(ROOT, "docs")
ap = argparse.ArgumentParser()
ap.add_argument("--repo", default="apisteme/ea-atlas")
ap.add_argument("--no-shots", action="store_true")
a = ap.parse_args()
GH = f"https://github.com/{a.repo}"
esc = html.escape
TMP = tempfile.mkdtemp()
SHOTS = os.path.join(DOCS, "assets", "shots")
old_shots = os.path.join(TMP, "old-shots")
if os.path.isdir(SHOTS):
    shutil.copytree(SHOTS, old_shots)
shutil.rmtree(DOCS, ignore_errors=True)
for d in ("downloads", "examples", "guides", "assets/shots"):
    os.makedirs(os.path.join(DOCS, d), exist_ok=True)
if os.path.isdir(old_shots):
    shutil.copytree(old_shots, SHOTS, dirs_exist_ok=True)
open(os.path.join(DOCS, ".nojekyll"), "w").close()
shutil.copy(os.path.join(SITE, "style.css"), os.path.join(DOCS, "assets", "style.css"))
shutil.copy(os.path.join(SITE, "episteme-logo.png"), os.path.join(DOCS, "assets", "episteme-logo.png"))
EP = "https://www.epistemepartners.com"
YEAR = "2026"


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit(f"Failed: {' '.join(cmd)}\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return r.stdout


def kb(p):
    n = os.path.getsize(p)
    return f"{n / 1048576:.1f} MB" if n > 1048576 else f"{max(1, n // 1024)} KB"


# ---------------------------------------------------------------- 1. kits
DL = os.path.join(DOCS, "downloads")
run([sys.executable, os.path.join(ROOT, "tools", "make_copilot_skill.py"), "--out", os.path.join(TMP, "cs")])
shutil.copy(os.path.join(TMP, "cs", "enterprise-architecture-atlas.zip"), os.path.join(DL, "enterprise-architecture-atlas-copilot-studio.zip"))
shutil.copy(os.path.join(TMP, "cs", "enterprise-architecture-atlas-folder.zip"), os.path.join(DL, "enterprise-architecture-atlas-copilot-studio-folder.zip"))
run([sys.executable, os.path.join(ROOT, "tools", "make_github_copilot_kit.py"), "--out", os.path.join(TMP, "gh")])
shutil.copy(os.path.join(TMP, "gh", "enterprise-architecture-atlas-github-copilot.zip"), DL)
cz = os.path.join(DL, "enterprise-architecture-atlas-claude.zip")
with zipfile.ZipFile(cz, "w", zipfile.ZIP_DEFLATED) as z:
    for d, dirs, fs in os.walk(SKILL):
        dirs[:] = sorted(x for x in dirs if x not in ("__pycache__", "node_modules", "output"))
        for f in sorted(fs):
            if f.endswith(".pyc"):
                continue
            p = os.path.join(d, f)
            z.write(p, "enterprise-architecture-atlas/" + os.path.relpath(p, SKILL).replace(os.sep, "/"))
for f in ("LICENSE", "LICENSE-CONTENT.md", "NOTICE.md"):
    with zipfile.ZipFile(cz, "a") as z:
        z.write(os.path.join(ROOT, f), "enterprise-architecture-atlas/" + f)
KITS = {
    "claude": ("Claude", "enterprise-architecture-atlas-claude.zip"),
    "copilot-studio": ("Microsoft Copilot Studio", "enterprise-architecture-atlas-copilot-studio.zip"),
    "github-copilot": ("GitHub Copilot", "enterprise-architecture-atlas-github-copilot.zip"),
}

# ---------------------------------------------------------------- 2. examples
EXAMPLES = json.load(open(os.path.join(SITE, "examples.json"), encoding="utf-8"))
env = dict(os.environ, ATLAS_ASSISTANT="your assistant")
for ex in EXAMPLES:
    src = os.path.join(ROOT, ex["sample"])
    ws = os.path.join(TMP, "ex-" + ex["id"])
    shutil.copytree(src, ws, ignore=shutil.ignore_patterns("output", "__pycache__"))
    run([sys.executable, os.path.join(SKILL, "engine", "build.py"), "--workspace", ws], env=env)
    D = json.load(open(os.path.join(ws, "repository", "data.json"), encoding="utf-8"))
    out = os.path.join(DOCS, "examples", ex["id"])
    os.makedirs(out)
    files = []
    for f in sorted(os.listdir(os.path.join(ws, "output"))):
        if f.endswith((".html", ".xlsx")):
            shutil.copy(os.path.join(ws, "output", f), out)
            files.append(f)
    bundle = os.path.join(out, f"{D['meta']['file_prefix']}_atlas_model.json")
    run([sys.executable, os.path.join(SKILL, "engine", "atlas_bundle.py"), "pack", "--workspace", ws, "--out", bundle])
    if ex.get("archimate"):
        shutil.copy(os.path.join(src, ex["archimate"]), out)
    ex["D"] = D
    ex["dashboard"] = next(f for f in files if f.endswith(".html"))
    ex["excel"] = next(f for f in files if f.endswith(".xlsx"))
    ex["bundle"] = os.path.basename(bundle)
    ex["dir"] = out

VIEWS = [
    ("overview", "Overview", "Portfolio health, data confidence and where attention is needed."),
    ("capabilities", "Capability map", "L1 to L3 capabilities with lenses: coverage, TIME, maturity, strategy, regulation."),
    ("strategy", "Strategic priorities", "Pillars and initiatives traced to journeys, capabilities and applications."),
    ("programme", "Programme", "What a merger, acquisition or transformation means for the architecture."),
    ("change", "Change impact", "Epics and features, and what each one changes."),
    ("scenarios", "What if?", "Outages, supplier failure, data centre loss, price and regulatory change."),
    ("pmap", "Process maps", "Swimlane map for each journey: roles, steps and systems."),
    ("apps", "Applications", "Portfolio by TIME rating, functional fit and technical health."),
    ("integration", "Integration map", "Data flows between applications, by layer and integration type."),
    ("resilience", "Resilience", "Data centre dependency and recovery readiness."),
    ("risk", "Third-party risk", "Critical outsourcing and the suppliers behind critical functions."),
    ("changes", "Change log", "Every release, compared field by field with the previous one."),
]

# ---------------------------------------------------------------- 3. screenshots
SHOT_VIEWS = [v[0] for v in VIEWS]
if not a.no_shots:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sync_playwright = None
        print("Playwright not installed: keeping existing screenshots")
    if sync_playwright:
        with sync_playwright() as p:
            b = p.chromium.launch()
            for ex in EXAMPLES:
                url = "file://" + os.path.join(ex["dir"], ex["dashboard"])
                for v in SHOT_VIEWS:
                    ctx = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
                    pg = ctx.new_page()
                    pg.goto(url + "#" + v)
                    pg.wait_for_timeout(600)
                    pg.screenshot(path=os.path.join(SHOTS, f"{ex['id']}-{v}.jpg"), type="jpeg", quality=82, clip={"x": 232, "y": 0, "width": 1208, "height": 755})
                    ctx.close()
            b.close()


def shot(exid, v):
    p = f"{exid}-{v}.jpg"
    return p if os.path.exists(os.path.join(SHOTS, p)) else ""


# ---------------------------------------------------------------- page frame

def frame(title, desc, body, cur, up):
    nav = [("Home", "index.html", "home"), ("Examples", "examples/index.html", "examples"),
           ("Get the kit", "index.html#kits", "kits"), ("Guides", "guides/claude.html", "guides"), ("GitHub", GH, "gh")]
    links = "".join(f'<a href="{h if h.startswith("http") else up + h}"{" aria-current=\"page\"" if k == cur else ""}>{n}</a>' for n, h, k in nav)
    return f"""<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="stylesheet" href="{up}assets/style.css">
<script>try{{var t=localStorage.getItem('ea-atlas-theme');if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
</head><body>
<header class="top"><div class="wrap"><a class="mark" href="{up}index.html"><img src="{up}assets/episteme-logo.png" alt="Episteme Partners" width="69" height="42"><span>EA Atlas</span></a><nav aria-label="Main">{links}</nav></div></header>
<main>{body}</main>
<footer><div class="wrap"><div>
<div class="by"><img src="{up}assets/episteme-logo.png" alt="" width="56" height="34"><span>EA Atlas is an open project by <a href="{EP}">Episteme Partners</a>, platform and architecture consulting, London.</span></div>
<p>Content is licensed under <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a> and code under the <a href="{GH}/blob/main/LICENSE">MIT licence</a>. ArchiSurance is a fictional company from the sample model that ships with <a href="https://www.archimatetool.com">Archi</a> (MIT licence). Industry standards (BIAN, ACORD, APQC) are referenced by name only; their content belongs to their publishers. Regulation summaries are paraphrased and are not legal advice.</p>
<p><a href="{GH}">Source on GitHub</a>, <a href="{GH}/blob/main/NOTICE.md">notices</a>, <a href="{GH}/issues">report a problem</a>.</p></div><div><button class="themebtn" type="button" id="theme">Switch theme</button></div>
<p class="copy">&copy; {YEAR} Episteme Partners Ltd. Content CC BY 4.0, code MIT.</p></div></footer>
<script>document.getElementById('theme').onclick=function(){{var r=document.documentElement,d=r.dataset.theme||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'),n=d==='dark'?'light':'dark';r.dataset.theme=n;try{{localStorage.setItem('ea-atlas-theme',n)}}catch(e){{}}}};</script>
</body></html>
"""


def write(rel, s):
    assert "—" not in s and "–" not in s, f"dash in {rel}: " + s[max(0, s.find("—") - 80):s.find("—") + 20]
    p = os.path.join(DOCS, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(s)


# ---------------------------------------------------------------- capability heat map
ORDER = ["Eliminate", "Migrate", "Tolerate", "Invest"]


def heatmap(ex, up):
    D = ex["D"]
    caps = D["capabilities"]
    weakest = {}
    for app in D["apps"]:
        for c in app.get("capabilities", []):
            t = app.get("time")
            if t in ORDER and (c not in weakest or ORDER.index(t) < ORDER.index(weakest[c])):
                weakest[c] = t
    dash = f"{up}examples/{ex['id']}/{ex['dashboard']}"
    cols, i = [], 0
    for l1 in [c for c in caps if c["level"] == 1]:
        tiles = []
        for c in [x for x in caps if x["parent"] == l1["id"]]:
            t = weakest.get(c["id"], "Gap")
            label = "no supporting application" if t == "Gap" else f"weakest application rating {t}"
            tiles.append(f'<a class="tile t-{t}" style="--i:{i}" href="{dash}#capabilities" title="{esc(c["name"])}: {label}">{esc(c["name"])}</a>')
            i += 1
        cols.append(f'<div class="dom"><h3>{esc(l1["name"])}</h3><div class="tiles">{"".join(tiles)}</div></div>')
    n_l2 = sum(1 for c in caps if c["level"] == 2)
    legend = "".join(f'<span><i class="t-{t}"></i>{t}</span>' for t in reversed(ORDER)) + '<span><i class="t-Gap"></i>No application</span>'
    return f"""<figure class="plate" aria-labelledby="plate-t">
<div class="plate-head"><h2 id="plate-t">{esc(D['meta']['organisation'])} capability map</h2>
<p>{n_l2} capabilities in {len(cols)} domains, each coloured by the weakest TIME rating among the applications that support it. Select one to open the full dashboard.</p></div>
<div class="map">{''.join(cols)}</div>
<div class="legend" aria-label="Legend">{legend}</div></figure>"""


# ---------------------------------------------------------------- home page
EX0 = EXAMPLES[0]
D0 = EX0["D"]
dash0 = f"examples/{EX0['id']}/{EX0['dashboard']}"
FLOW_SVG = """<div class="scroll"><svg viewBox="0 0 1000 330" role="img" aria-labelledby="flow-t flow-d" style="min-width:640px;width:100%;height:auto;margin-top:34px;font-family:var(--sans)">
<title id="flow-t">How inputs become the dashboard and Excel</title>
<desc id="flow-d">Inputs such as inventories, supplier registers, org charts, strategy papers, Archi models and conversation go into the model. The build scripts turn the model into a dashboard, an Excel repository, an atlas file and a change log. The next refresh starts from the updated model.</desc>
<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="var(--ink-2)"/></marker></defs>
<g font-size="14" fill="var(--ink)">
<text x="0" y="18" font-weight="600" fill="var(--ink-2)">What you bring</text>
""" + "".join(f'<rect x="0" y="{32 + k * 44}" width="230" height="34" rx="5" fill="var(--band)" stroke="var(--rule)"/><text x="14" y="{54 + k * 44}">{t}</text>'
              for k, t in enumerate(["Application inventory", "Supplier register, contracts", "Org chart, RACI", "Processes, journeys", "Strategy, regulation, backlog", "Archi model, or just tell it"])) + """
<text x="330" y="18" font-weight="600" fill="var(--ink-2)">Your assistant and the scripts</text>
<rect x="330" y="60" width="270" height="78" rx="6" fill="none" stroke="var(--accent)" stroke-width="2"/>
<text x="348" y="92" font-weight="600">Model</text><text x="348" y="116" fill="var(--ink-2)" font-size="13">JSON files, every item tagged</text>
<rect x="330" y="176" width="270" height="78" rx="6" fill="var(--accent)"/>
<text x="348" y="208" font-weight="600" fill="#fff">Build</text><text x="348" y="232" fill="#fff" font-size="13">validate, impact engines, diff</text>
<path d="M465 140V172" stroke="var(--ink-2)" stroke-width="1.5" marker-end="url(#ar)"/>
<path d="M232 165H326" stroke="var(--ink-2)" stroke-width="1.5" marker-end="url(#ar)"/>
<text x="700" y="18" font-weight="600" fill="var(--ink-2)">What you get</text>
""" + "".join(f'<rect x="700" y="{40 + k * 54}" width="300" height="42" rx="5" fill="var(--band)" stroke="var(--rule)"/><text x="716" y="{66 + k * 54}">{t}</text>'
              for k, t in enumerate(["Clickable dashboard (HTML)", "Excel repository", "Atlas file (the whole model)", "Change log for this release"])) + """
<path d="M602 215H696" stroke="var(--ink-2)" stroke-width="1.5" marker-end="url(#ar)"/>
<path d="M850 262V300H465V258" fill="none" stroke="var(--accent)" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#ar)"/>
<text x="560" y="320" font-size="13" fill="var(--ink-2)">next refresh starts from the updated model</text>
</g></svg></div>"""

RESPONDS = [
    ("Application inventory", "Applications, Landscape map, capability coverage, Support and lifecycle"),
    ("Supplier register and contracts", "Suppliers, Contracts and licences, Third-party risk, concentration"),
    ("Org chart and RACI", "Roles, swimlanes in Process maps, who is affected in What if?"),
    ("Process documents", "Process architecture, journeys and their steps"),
    ("Interface catalogue", "Integration map, and how far an outage spreads in What if?"),
    ("DR tests and data centre facts", "Resilience, recovery times in every scenario"),
    ("Strategy papers", "Strategic priorities traced to journeys, capabilities and applications"),
    ("A regulation or its update", "Regulatory readiness lens on the capability map, requirement checks"),
    ("Change backlog", "Change impact for every epic and feature"),
    ("A merger or transformation plan", "Programme view: commitments, cost pool, decisions, contract exposure"),
    ("An Archi model", "Drafts of all of the above, refreshed on the next import rather than duplicated"),
]
PACKS = [("core", "Any industry", "APQC PCF categories", "NIS2, GDPR, EU AI Act"),
         ("banking", "Banks", "BIAN service domains", "DORA, EU PSR, EU AI Act"),
         ("insurance", "Insurers", "ACORD-style insurance domains", "DORA, Solvency II review, EU AI Act")]
TAGS = [("Customer-provided", "Confirmed by you or a file you supplied.", "--invest"),
        ("Public", "Confirmed by a cited public source, with its link.", "--tolerate"),
        ("Partly confirmed", "Capability confirmed, product or vendor still to confirm.", "--migrate"),
        ("Illustrative", "A placeholder until real data replaces it.", "--ink-2")]


def kit_block(k, who, how, lives, share, extra=""):
    name, z = KITS[k]
    return f"""<div class="kit"><h3>{name}</h3><p class="for">{who}</p>
<dl><dt>Runs the scripts</dt><dd>{how}</dd><dt>The atlas lives</dt><dd>{lives}</dd><dt>Sharing the dashboard</dt><dd>{share}</dd></dl>
<div class="actions"><a class="btn primary small" href="downloads/{z}" download>Download ({kb(os.path.join(DL, z))})</a><a class="btn small" href="guides/{k}.html">Setup guide</a></div>{extra}</div>"""


m = D0["meta"]
home = f"""
<section class="hero"><div class="wrap">
<h1>Map your organisation <span>without buying an EA tool</span></h1>
<p class="lede">EA Atlas turns what you know about your organisation into a clickable dashboard and an Excel repository: capabilities, journeys, processes, roles, applications, suppliers, risk and regulation, all linked. Your AI assistant does the modelling. Open-source scripts do the building, the same way every time.</p>
<div class="actions"><a class="btn primary" href="examples/index.html">Browse the examples</a><a class="btn" href="#kits">Get the kit for your assistant</a></div>
</div></section>
<div class="wide">{heatmap(EX0, "")}</div>

<section class="band" id="what"><div class="wrap intro">
<div><h2>One model, two outputs, every change recorded</h2>
<p>Commercial EA platforms cost more than many architecture teams can justify. Most teams fall back on spreadsheets and slides that drift apart. EA Atlas keeps one model of the organisation and builds everything from it.</p>
<p>You talk to your assistant the way you would brief a colleague. It writes the model, runs the build and tells you what changed. Nothing is hand-drawn, so the dashboard and the Excel always agree.</p></div>
<ul class="facts">
<li><b>Built from the model</b>The dashboard and Excel are generated, never edited by hand, so they cannot contradict each other.</li>
<li><b>Works offline</b>The dashboard is a single HTML file. Open it in any browser, email it or put it on an intranet.</li>
<li><b>Releases, not edits</b>Every refresh raises the version and compares the model field by field with the last release.</li>
<li><b>Any industry</b>Industry packs supply the capability model, roles, journeys, regulations and vocabulary.</li>
<li><b>Honest about data</b>Every application and supplier says where its facts came from, and placeholders are labelled.</li>
<li><b>Bring Archi</b>Import an Archi model or Open Group exchange file instead of starting from scratch.</li>
</ul></div></section>

<section class="band" id="how"><div class="wrap">
<h2>How it works</h2>
<ol class="flow">
<li><h3>Bring what you have</h3><p>Inventories, supplier registers, org charts, strategy papers, an Archi model, public reports, or just describe it in the chat.</p></li>
<li><h3>The assistant writes the model</h3><p>It matches each fact to the model, asks about anything uncertain, and tags each item with where it came from.</p></li>
<li><h3>The scripts build</h3><p>Every reference is checked, the impact engines run, and the dashboard, Excel and atlas file are written.</p></li>
<li><h3>Each refresh is a release</h3><p>New information raises the version. The change log shows what was added, changed or retired, and why.</p></li>
</ol>
{FLOW_SVG}
</div></section>

<section class="band" id="inputs"><div class="wrap">
<h2>What each kind of input changes</h2>
<p>You do not need everything on day one. Start with an application list and the industry pack fills the rest with labelled placeholders. Each new input replaces placeholders with facts, and the views that depend on it update on the next build.</p>
<div class="scroll"><table class="tbl"><thead><tr><th>When you provide</th><th>These views change</th></tr></thead><tbody>
{''.join(f'<tr><td>{esc(i)}</td><td class="views">{esc(v)}</td></tr>' for i, v in RESPONDS)}
</tbody></table></div>
<ul class="tags">{''.join(f'<li style="--c:var({c})"><b>{esc(t)}</b>{esc(d)}</li>' for t, d, c in TAGS)}</ul>
<p class="note">A higher tag is never overwritten by a lower one. Costs, contract terms, SLAs and recovery targets you have not supplied are generated and tagged Illustrative, so the dashboard is complete from the start without pretending to know.</p>
</div></section>

<section class="band" id="outputs"><div class="wrap">
<h2>What you get</h2>
<div class="outs">
<div class="shots three">
{''.join(f'<figure class="shot"><a href="{dash0}#{v}"><img src="assets/shots/{shot(EX0["id"], v)}" alt="{esc(n)} view of the {esc(m["organisation"])} dashboard" width="1208" height="755"></a><figcaption>{esc(n)}</figcaption></figure>' for v, n in (("capabilities", "Capability map"), ("scenarios", "What if?"), ("pmap", "Process maps")) if shot(EX0["id"], v))}
</div>
<ul class="outlist">
<li><b>The dashboard</b><span>More than 20 views across strategy, business, technology and commercial: capability map with lenses, swimlane process maps, RACI, TIME portfolio, landscape and integration maps, resilience, suppliers, contracts and licences, third-party risk, regulatory readiness, change impact, what-if scenarios, traceability and the change log.</span></li>
<li><b>The Excel repository</b><span>One tab per element and relationship, with formulas for utilisation, notice deadlines and end of support. Laid out for import into EA tools if you move to one later.</span></li>
<li><b>The atlas file</b><span>The whole model and its history in one JSON file. Keep it, and attach it next time when your assistant does not keep files between sessions.</span></li>
<li><b>What if and change impact</b><span>Pick an outage, a supplier failure or a planned change and see the journeys, roles, critical functions, recovery times and costs affected, in the dashboard or by asking your assistant.</span></li>
</ul></div></div></section>

<section class="band" id="kits"><div class="wrap">
<h2>Use it with your assistant</h2>
<p>The same engine and the same dashboard in three kits. Pick the assistant your organisation already uses.</p>
<div class="kits">
{kit_block("claude", "For Claude on the web, desktop and mobile, and Claude Code. The most complete version: Claude reads attachments in any format and researches public sources.", "In its own workspace", "In Claude, or in your project folder with Claude Code", "Published as a page with its own link, updated on every release")}
{kit_block("copilot-studio", "For organisations on Microsoft 365. Build an agent in Copilot Studio, upload the skill, and publish it to Teams or Microsoft 365 Copilot.", "In the agent's Python sandbox", "In the atlas file you keep in OneDrive or SharePoint", "As a file, or on SharePoint")}
{kit_block("github-copilot", "For architects who work in a Git repository with VS Code. Copilot runs the build in your terminal, and every release is a commit you can review.", "In your VS Code terminal", "In <code>ea-atlas/</code> in your repository", "From the repository, or an internal site")}
</div>
<p class="note">No assistant at all? The build runs by hand with Python 3: copy a sample, edit the JSON files and run <code>build.py</code>. See the <a href="{GH}#readme">README</a>.</p>
</div></section>

<section class="band" id="packs"><div class="wrap">
<h2>Industry packs</h2>
<p>The engine knows nothing about any industry. A pack supplies the capability model, typical roles, journeys and processes, a regulation library, a glossary and the labels the dashboard uses, such as what "critical" means for that industry.</p>
<div class="scroll"><table class="tbl"><thead><tr><th>Pack</th><th>For</th><th>Capability reference</th><th>Regulation library</th></tr></thead><tbody>
{''.join(f'<tr><td><code>{p}</code></td><td>{w}</td><td>{c}</td><td>{r}</td></tr>' for p, w, c, r in PACKS)}
</tbody></table></div>
<p class="note">Need another industry? Ask your assistant to write a pack, or contribute one: see <a href="{GH}/blob/main/plugins/enterprise-architecture-atlas/skills/enterprise-architecture-atlas/reference/pack-authoring.md">pack authoring</a>.</p>
</div></section>

<section class="band contact" id="contact"><div class="wrap">
<h2>Get in touch</h2>
<p>EA Atlas is free to use. If you would like help setting up an atlas, an industry pack for your sector, or a review of your architecture, Episteme Partners can help.</p>
<div class="actions"><a class="btn primary" href="mailto:info@epistemepartners.com">Contact Episteme Partners</a><a class="btn" href="{EP}">Visit epistemepartners.com</a></div>
</div></section>
"""
write("index.html", frame("EA Atlas", "A do-it-yourself enterprise architecture atlas: build a clickable dashboard and Excel repository of your organisation with Claude, Microsoft Copilot or GitHub Copilot.", home, "home", ""))


# ---------------------------------------------------------------- examples
def stats(D):
    l2 = sum(1 for c in D["capabilities"] if c["level"] == 2)
    return [(len(D["apps"]), "applications"), (l2, "capabilities"), (len(D["suppliers"]), "suppliers"),
            (len(D["value_streams"]), "journeys")]


tiles = []
for ex in EXAMPLES:
    D = ex["D"]
    th = shot(ex["id"], "overview")
    st = "".join(f"<li><b>{n}</b>{t}</li>" for n, t in stats(D))
    tiles.append(f"""<article class="ex">
<a class="thumb" href="{ex['id']}/index.html">{f'<img src="../assets/shots/{th}" alt="" loading="lazy" width="1208" height="755">' if th else ''}</a>
<div class="body"><h2><a href="{ex['id']}/index.html">{esc(ex['title'])}</a></h2><div class="meta">{esc(ex['meta'])}, version {esc(D['meta']['version'])}</div>
<p>{esc(ex['blurb'])}</p><ul class="stats">{st}</ul>
<div class="actions"><a class="btn primary small" href="{ex['id']}/{ex['dashboard']}">Open dashboard</a><a class="btn small" href="{ex['id']}/index.html">Details and downloads</a></div></div></article>""")
tiles.append("""<article class="ex own"><div class="body"><h2>Your organisation</h2>
<p>Pick the kit for your assistant, choose an industry pack, and start with whatever you have: an application list, a supplier register or an Archi model.</p>
<div class="actions"><a class="btn small" href="../index.html#kits">Get the kit</a></div></div></article>""")
gal = f"""<div class="pagehead"><div class="wrap"><p class="crumb"><a href="../index.html">Home</a></p><h1>Examples</h1>
<p>Each example is a complete atlas built by the same scripts you will use. Open the dashboard in your browser, or download the Excel and the atlas file to see exactly what your assistant produces.</p></div></div>
<div class="wrap page"><div class="gallery" style="margin-top:0">{''.join(tiles)}</div></div>"""
write("examples/index.html", frame("Examples, EA Atlas", "Example enterprise architecture atlases built with EA Atlas.", gal, "examples", "../"))

for ex in EXAMPLES:
    D = ex["D"]
    dash = ex["dashboard"]
    def vimg(v):
        s = shot(ex["id"], v)
        return f'<img src="../../assets/shots/{s}" alt="" loading="lazy" width="1208" height="755">' if s else ""
    vg = "".join(f'<a href="{dash}#{v}">{vimg(v)}<h3>{esc(n)}</h3><p>{esc(s)}</p></a>'
                 for v, n, s in VIEWS if v != "programme" or D.get("programme"))
    downloads = [(dash, "Dashboard", "Open in any browser; works offline"), (ex["excel"], "Excel repository", "One tab per element and relationship"),
                 (ex["bundle"], "Atlas file", "The whole model and its history; attach it to your assistant to refresh or ask questions")]
    if ex.get("archimate"):
        downloads.append((ex["archimate"], "Archi model", "The source model; open it in Archi or import it again"))
    dl = "".join(f'<li><a href="{f}"{"" if f.endswith(".html") else " download"}>{n}</a><span>{d}, {kb(os.path.join(ex["dir"], f))}</span></li>' for f, n, d in downloads)
    ctx = "".join(f"<li>{esc(c)}</li>" for c in D["meta"].get("context", []))
    body = f"""<div class="pagehead"><div class="wrap"><p class="crumb"><a href="../index.html">Examples</a></p>
<h1>{esc(ex['title'])}</h1><p>{esc(ex['meta'])}. Version {esc(D['meta']['version'])}, released {esc(D['meta']['release_date'])}.</p></div></div>
<div class="wrap page"><div class="intro"><div><p>{esc(ex['blurb'])}</p><ul>{ctx}</ul>
<div class="actions"><a class="btn primary" href="{dash}">Open the dashboard</a></div></div>
<div><h2 style="font-size:1.3rem">Downloads</h2><ul class="dl">{dl}</ul></div></div>
<h2 style="margin-top:64px">Go straight to a view</h2>
<div class="viewgrid">{vg}</div>
<div class="callout" style="margin-top:48px"><p><b>Try a refresh yourself.</b> Download the atlas file, attach it in a chat with your assistant and ask, for example: "Add a new claims application from a SaaS vendor and retire the old one", or "What happens if the payment network is down for a day?"</p></div>
</div>"""
    write(f"examples/{ex['id']}/index.html", frame(f"{ex['title']}, EA Atlas example", ex["blurb"], body, "examples", "../../"))

# ---------------------------------------------------------------- guides
import markdown
GUIDE_NOTE = {
    "claude": "",
    "copilot-studio": "<p>You do not need to run the build script below: the package is ready. Download <a href='../downloads/enterprise-architecture-atlas-copilot-studio.zip'>the skill zip</a>, and if Copilot Studio rejects it, <a href='../downloads/enterprise-architecture-atlas-copilot-studio-folder.zip'>the folder version</a>.</p>",
    "github-copilot": "",
}
for k, (name, z) in KITS.items():
    md = open(os.path.join(ROOT, "kits", k, "README.md"), encoding="utf-8").read()
    h = markdown.markdown(md, extensions=["tables", "fenced_code"])
    h = re.sub(r"<h1>.*?</h1>", "", h, count=1)
    side = "".join(f'<a class="btn small" href="{kk}.html"{" aria-current=page" if kk == k else ""}>{nn}</a>' for kk, (nn, _) in KITS.items())
    body = f"""<div class="pagehead"><div class="wrap"><p class="crumb"><a href="../index.html#kits">Kits</a></p><h1>Set up EA Atlas for {esc(name)}</h1>
<div class="kitnav">{side}</div></div></div>
<div class="wrap page"><div class="callout"><p><a href="../downloads/{z}" download><b>Download {z}</b></a> ({kb(os.path.join(DL, z))})</p>{GUIDE_NOTE[k]}</div>
<div class="prose">{h}</div></div>"""
    write(f"guides/{k}.html", frame(f"{name} setup, EA Atlas", f"How to install and use EA Atlas with {name}.", body, "guides", "../"))

shutil.rmtree(TMP, ignore_errors=True)
total = 0
for d, _, fs in os.walk(DOCS):
    for f in fs:
        total += os.path.getsize(os.path.join(d, f))
print(f"Site written to {DOCS}, {total / 1048576:.1f} MB")
for d, _, fs in sorted(os.walk(DOCS)):
    for f in sorted(fs):
        p = os.path.join(d, f)
        print(f"  {os.path.relpath(p, DOCS)}  {kb(p)}")
