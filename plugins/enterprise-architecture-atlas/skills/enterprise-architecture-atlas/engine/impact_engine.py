#!/usr/bin/env python3
"""Python port of scenario_engine.js and feature_engine.js, for hosts without Node (for example the
Copilot Studio and Agent Builder sandboxes). It must give exactly the same results as the JavaScript
engines the dashboard runs; test_engine_parity.js checks this. When you change one engine, change the
other in the same way.

    python3 impact_engine.py --workspace path/to/ea-atlas
writes repository/scenario_results.json and repository/feature_results.json, like compute_scenarios.js.
"""
import json, os, re, math, argparse
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN

# ---------------------------------------------------------------- helpers that mirror JavaScript behaviour
def js_round(x):
    """Math.round: halves round towards positive infinity."""
    return int(math.floor(x + 0.5))


def js_fixed2(x):
    """Number(x.toFixed(2)): exact binary value, ties to the larger value."""
    d = Decimal(x)
    q = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP if d >= 0 else ROUND_HALF_DOWN)
    v = float(q)
    return 0.0 if v == 0 else v


def uniq(a, skip_none=False):
    o = []
    for x in a:
        if skip_none and x is None:
            continue
        if x not in o:
            o.append(x)
    return o


def js_str(v):
    return "undefined" if v is None else str(v)


# ---------------------------------------------------------------- scenario engine
TYPES = {
    "app_outage": dict(label="Application outage", target="app", disruptive=True),
    "platform_failure": dict(label="Platform failure", target="platform", disruptive=True),
    "supplier_failure": dict(label="Supplier failure or exit", target="sup", disruptive=True),
    "dc_loss": dict(label="Data centre loss", target="dc", disruptive=True),
    "decommission": dict(label="Replace or decommission", target="app", disruptive=False),
    "price_change": dict(label="Supplier price change", target="sup", disruptive=False),
    "regulatory_change": dict(label="Regulatory change", target="requirement", disruptive=False),
}
LEVELS = ["Low", "Medium", "High", "Critical"]
SIZE_POINTS = {"S": 1, "M": 3, "L": 8}


class _Idx:
    def __init__(self, D):
        self.AP = {a["id"]: a for a in D["apps"]}
        self.ST = {s["id"]: s for s in D["steps"]}
        self.VS = {v["id"]: v for v in D["value_streams"]}
        self.CVS = {c["id"]: c for c in D["customer_value_streams"]}
        self.SU = {s["id"]: s for s in D["suppliers"]}
        self.RES = {r["app"]: r for r in D.get("resilience") or []}
        self.LIC = {l["app"]: l for l in D["licences"]}
        self.SUP = {s["app"]: s for s in D["support"]}
        self.K = {}
        for k in D["contracts"]:
            self.K[k["supplier"]] = k
        self.appSteps = {a["id"]: [] for a in D["apps"]}
        for s in D["steps"]:
            for a in s["apps"]:
                if a in self.appSteps:
                    self.appSteps[a].append(s["id"])
        self.appSups = {a["id"]: [] for a in D["apps"]}
        for x in D["app_supplier"]:
            if x["app"] in self.appSups:
                self.appSups[x["app"]].append(x)


_cache = {}


def _idx(D):
    k = id(D)
    if k not in _cache:
        _cache[k] = _Idx(D)
    return _cache[k]


def cost(I, aid):
    return ((I.LIC.get(aid) or {}).get("annual_cost_m") or 0) + ((I.SUP.get(aid) or {}).get("annual_support_cost_m") or 0)


def run_scenario(D, sc):
    I = _idx(D)
    T = TYPES.get(sc.get("type"), TYPES["app_outage"])
    typ = sc.get("type")
    targets = sc.get("targets") or []
    down, degraded, atRisk, changed, notes = {}, {}, {}, {}, []

    def mark(m, aid, why):
        if aid not in I.AP:
            return False
        if aid in down or aid in changed:
            return False
        if aid in m:
            return False
        m[aid] = why
        return True

    if typ in ("app_outage", "platform_failure"):
        for aid in targets:
            mark(down, aid, "Directly affected")
    if typ == "supplier_failure":
        for sid in targets:
            for x in [x for x in D["app_supplier"] if x["supplier"] == sid]:
                nm = js_str((I.SU.get(sid) or {}).get("name"))
                if re.search(r"AMS|SI|Integration|Agency", x["role"], re.I) and not re.search(r"Product|In-house|Hosting|Virtualisation|Container|Platform|Scheme", x["role"], re.I):
                    mark(degraded, x["app"], nm + " provides " + x["role"] + "; change and support at risk")
                else:
                    mark(down, x["app"], nm + " is " + x["role"].lower())
    if typ == "dc_loss":
        DCS = D.get("data_centres") or []
        model = (D.get("meta") or {}).get("dc_model") or "single"
        P1 = next((d for d in DCS if d.get("kind") == "primary"), DCS[0] if DCS else None)
        P2 = next((d for d in DCS if d.get("kind") == "secondary"), DCS[1] if len(DCS) > 1 else None)
        lostP = bool(P1 and P1["id"] in targets)
        lostS = bool(P2 and P2["id"] in targets)
        for a in D["apps"]:
            if a.get("site") != "internal":
                continue
            if model == "active-active":
                if lostP and lostS:
                    mark(down, a["id"], "Both sites lost")
                elif lostP or lostS:
                    mark(atRisk, a["id"], "Runs on one site only until " + (P1["name"] if lostP else P2["name"]) + " is restored")
            elif model == "active-passive" and P2:
                if lostP:
                    mark(down, a["id"], "Runs live in " + P1["name"] + "; needs site failover to " + P2["name"])
                elif lostS:
                    mark(atRisk, a["id"], "Loses its " + P2["name"] + " standby; no site failover available")
            elif lostP:
                mark(down, a["id"], "Runs in " + P1["name"] + "; restore from backup")
        if model == "active-passive" and P2:
            if lostP:
                notes.append("Active-passive: every in-house application is down until the site failover to " + P2["name"] + " completes. Recovery time is set by the failover runbook and the slowest critical application.")
            if lostS and not lostP:
                notes.append("No immediate outage. " + P1["name"] + " keeps running, but there is no secondary site until " + P2["name"] + " is restored, so any failure in that window has no recovery path.")
        elif model == "active-active" and (lostP or lostS):
            notes.append("Active-active: the remaining site carries the load. Check capacity and that every critical application is deployed on both sites.")
        elif lostP:
            notes.append("Single site: in-house applications must be rebuilt and restored from backup elsewhere. Recovery is likely to exceed most recovery targets.")
    if typ == "decommission":
        for aid in targets:
            if aid in I.AP:
                changed[aid] = "Retired or replaced"
    if typ == "price_change":
        for sid in targets:
            for a in D["apps"]:
                if a["vendor"] == sid:
                    changed[a["id"]] = "Licence and support repriced"

    if T["disruptive"] and typ != "dc_loss":
        grew, guard = True, 0
        while grew and guard < 10:
            guard += 1
            grew = False
            for p in list(down.keys()):
                for a in D["apps"]:
                    for r in a.get("runs_on") or []:
                        if r["app"] == p and mark(down, a["id"], "Runs on " + I.AP[p]["name"]):
                            grew = True
                hosts = (I.AP[p].get("platform") or {}).get("hosts") or []
                if hosts:
                    for a in D["apps"]:
                        if any((a.get("hosting") or "").startswith(h) for h in hosts) and a["id"] != p and mark(down, a["id"], "Hosted on " + I.AP[p]["name"]):
                            grew = True
        for pa in D["apps"]:
            c = (pa.get("platform") or {}).get("carries")
            if not c or pa["id"] not in down:
                continue
            rx = re.compile(c, re.I)
            for i in D["interfaces"]:
                if rx.search(i["protocol"]):
                    for x in (i["source_app"], i["target_app"]):
                        mark(degraded, x, "Loses " + pa["name"] + " flow: " + i["data"])
        for pa in D["apps"]:
            n = (pa.get("platform") or {}).get("note")
            if n and pa["id"] in down:
                notes.append(n)
        for i in D["interfaces"]:
            if i["source_app"] in down and i["target_app"] not in down:
                mark(degraded, i["target_app"], "No data from " + I.AP[i["source_app"]]["name"] + " (" + i["data"] + ")")
            if i["target_app"] in down and i["source_app"] not in down:
                mark(degraded, i["source_app"], "Cannot reach " + I.AP[i["target_app"]]["name"] + " (" + i["data"] + ")")
    if typ == "decommission":
        for a in D["apps"]:
            for r in a.get("runs_on") or []:
                if r["app"] in changed:
                    mark(atRisk, a["id"], "Must be re-hosted: runs on " + I.AP[r["app"]]["name"])
        for i in D["interfaces"]:
            if i["source_app"] in changed and i["target_app"] not in changed:
                mark(degraded, i["target_app"], "Interface to rework: " + i["data"])
            if i["target_app"] in changed and i["source_app"] not in changed:
                mark(degraded, i["source_app"], "Interface to rework: " + i["data"])

    reqs, reqCaps, reqProcs, effort, reg = [], [], [], 0, None
    if typ == "regulatory_change":
        regs = D.get("regulations") or []
        reg = next((r for r in regs if r["id"] == sc.get("regulation")), regs[0] if regs else None)
        if reg:
            reqs = [q for q in reg["requirements"] if not targets or q["id"] in targets]
            for q in reqs:
                for aid in q["apps"]:
                    if aid not in I.AP:
                        continue
                    changed[aid] = changed[aid] + "; " + q["id"] if aid in changed else q["id"] + " " + q["short"]
                reqCaps += q["caps"]
                reqProcs += q["procs"]
                effort += SIZE_POINTS.get(q.get("size"), 0)
    primary = list(down.keys()) + list(changed.keys())
    allx = uniq(primary + list(degraded.keys()) + list(atRisk.keys()))
    stepsHit = uniq([s for aid in primary for s in I.appSteps.get(aid, [])])
    stepsDeg = [s for s in uniq([s for aid in list(degraded.keys()) + list(atRisk.keys()) for s in I.appSteps.get(aid, [])]) if s not in stepsHit]
    steps = stepsHit + stepsDeg
    journeys = uniq([I.ST[s]["vs"] for s in steps])
    cvs = uniq([I.VS[v]["parent"] for v in journeys])
    caps = uniq(reqCaps) if typ == "regulatory_change" else uniq([c for aid in allx for c in I.AP[aid]["capabilities"]])
    procs = uniq(reqProcs) if typ == "regulatory_change" else [b["id"] for b in D["business_processes"] if b["level"] == 2 and any(aid in allx for aid in b["apps"])]
    roles = uniq([r for s in stepsHit for r in I.ST[s]["R"] + [I.ST[s]["A"]] + I.ST[s]["C"]])
    ifs = [i["id"] for i in D["interfaces"] if i["source_app"] in primary or i["target_app"] in primary]
    sups = uniq([x["supplier"] for aid in allx for x in I.appSups[aid]])
    critical = [aid for aid in primary if I.AP[aid]["tier_n"] <= 1]
    rtoPool = [aid for aid in primary if I.AP[aid]["tier_n"] <= 1 and aid in I.RES] if typ in ("dc_loss", "app_outage", "platform_failure", "supplier_failure") else []
    slow = None
    for aid in rtoPool:
        if not slow or I.RES[aid]["rto_hours"] > I.RES[slow]["rto_hours"]:
            slow = aid
    drIssues = [aid for aid in primary if aid in I.RES and re.search(r"Failed|issues|Not tested", I.RES[aid]["dr_result"])]
    costAtStake = 0
    for aid in primary:
        costAtStake = costAtStake + cost(I, aid)
    costDelta = 0
    if typ == "price_change":
        try:
            pct = float(sc.get("pct") or 0)
        except (TypeError, ValueError):
            pct = 0
        costDelta = costAtStake * pct / 100
    if typ == "decommission":
        costDelta = -costAtStake
    crit = len([aid for aid in primary if I.AP[aid].get("crit")])
    critDeg = len([aid for aid in list(degraded.keys()) + list(atRisk.keys()) if I.AP[aid].get("crit")])
    tier0 = len([aid for aid in primary if I.AP[aid]["tier_n"] == 0])
    vsCount = len([c for c in cvs if not (I.CVS.get(c) or {}).get("cross_cutting")])
    if typ == "price_change":
        total = 0
        for a in D["apps"]:
            total = total + cost(I, a["id"])
        total = total or 1
        m = abs(costDelta) / total
        level = "Critical" if m >= 0.05 else "High" if m >= 0.025 else "Medium" if m >= 0.006 else "Low"
        score = js_round(m * 1000)
    else:
        tier0Deg = len([aid for aid in degraded if I.AP[aid]["tier_n"] == 0])
        score = tier0 * 12 + crit * 2 + critDeg + tier0Deg * 3 + vsCount * 3 + len(journeys)
        if typ == "dc_loss" and len(down) == 0:
            score = js_round(score / 3)
        level = "Critical" if score >= 45 else "High" if score >= 22 else "Medium" if score >= 9 else "Low"
    return dict(type=typ, typeLabel=T["label"], disruptive=T["disruptive"], down=down, degraded=degraded, atRisk=atRisk, changed=changed,
                primary=primary, all=allx, steps=steps, stepsHit=stepsHit, journeys=journeys, cvs=cvs, caps=caps, procs=procs, roles=roles,
                ifs=ifs, sups=sups, critical=critical, crit=crit, critDegraded=critDeg, tier0=tier0, valueStreams=vsCount,
                slowestRto=dict(app=slow, hours=I.RES[slow]["rto_hours"]) if slow else None, drIssues=drIssues,
                costAtStake=costAtStake, costDelta=costDelta, score=score, level=level, notes=notes,
                reqs=[q["id"] for q in reqs], effort=effort, regulation=reg["id"] if reg else None)


def risk_rating(level, likelihood):
    try:
        l = float(likelihood or 0)
    except (TypeError, ValueError):
        l = 0
    r = l * (LEVELS.index(level) + 1 if level in LEVELS else 0)
    return "Critical" if r >= 12 else "High" if r >= 8 else "Medium" if r >= 4 else "Low"


# ---------------------------------------------------------------- change impact engine
CHANGE_W = {"Retire": 2, "Replace": 2, "New": 1.5, "Integrate": 1.5, "Enhance": 1, "Configure": 0.5}
TIER_W = [8, 5, 3, 1]


def q2n(q):
    m = re.match(r"^(\d{4})-Q([1-4])$", q or "")
    return int(m.group(1)) * 4 + (int(m.group(2)) - 1) if m else None


def dateQ(d):
    m = re.match(r"^(\d{4})-(\d{2})", d or "")
    return m.group(1) + "-Q" + str((int(m.group(2)) - 1) // 3 + 1) if m else None


class _FIdx(_Idx):
    def __init__(self, D):
        super().__init__(D)
        self.REQ = {}
        for r in D.get("regulations") or []:
            for q in r["requirements"]:
                self.REQ[q["id"]] = dict(q=q, reg=r)
        prog = D.get("programme") or {}
        self.BD = {b["id"]: b for b in prog.get("decisions") or []}
        self.PH = [[p["name"], p["start"]] for p in prog.get("phases") or [] if isinstance(p, dict) and p.get("start")]
        self.CUST = (D.get("meta") or {}).get("customer_role") or ""
        self.PROF = (D.get("meta") or {}).get("profile") or {}
        self.SI = {s["id"]: s for s in (D.get("strategy") or {}).get("initiatives") or []}
        self.C3 = {c["id"]: c for c in D.get("capabilities_l3") or []}


_fcache = {}


def _fidx(D):
    k = id(D)
    if k not in _fcache:
        _fcache[k] = _FIdx(D)
    return _fcache[k]


def _flag(sev, kind, text):
    return dict(sev=sev, kind=kind, text=text)


def run_feature(D, f, others=None):
    I = _fidx(D)
    flags = []
    apps = f.get("apps") or {}
    ids = [a for a in apps if a in I.AP]
    tq = q2n(f.get("target"))
    direct = [dict(app=a, change=apps[a], tier=I.AP[a]["tier_n"], crit=I.AP[a].get("crit"), time=I.AP[a]["time"]) for a in ids]
    partners, ifsRework, ifsTest = {}, [], []
    for i in D["interfaces"]:
        s, t = i["source_app"] in ids, i["target_app"] in ids
        if not (s or t) or (s and t):
            if s and t:
                ifsTest.append(i["id"])
            continue
        me = i["source_app"] if s else i["target_app"]
        other = i["target_app"] if s else i["source_app"]
        rework = apps[me] in ("Replace", "Retire")
        (ifsRework if rework else ifsTest).append(i["id"])
        p = partners.setdefault(other, dict(app=other, action="Regression test", ifs=[]))
        if rework:
            p["action"] = "Rework interface"
        p["ifs"].append(i["id"])
    platforms = [p for p in uniq([r["app"] for a in ids for r in I.AP[a].get("runs_on") or []], True) if p not in ids]
    caps3 = [c for c in f.get("caps") or [] if c in I.C3]
    caps2 = uniq([I.C3[c]["parent"] for c in caps3], True)
    stepsChanged = [s for s in f.get("steps") or [] if s in I.ST]
    stepsTouched = [s for s in uniq([s for a in ids for s in ([] if apps[a] == "Configure" else I.appSteps[a])], True) if s not in stepsChanged]
    journeys = uniq([I.ST[s]["vs"] for s in stepsChanged + stepsTouched], True)
    cvs = uniq([I.VS[v]["parent"] for v in journeys], True)
    procs = [b["id"] for b in D["business_processes"] if b["level"] == 2 and any(a in ids for a in b["apps"])]
    retrain = uniq([r for s in stepsChanged for r in I.ST[s]["R"] + [I.ST[s]["A"]]], True)
    inform = [r for r in uniq([r for s in stepsTouched for r in I.ST[s]["R"] + [I.ST[s]["A"]]], True) if r not in retrain]
    techOwners = uniq([I.AP[a].get("tech_owner") for a in ids], True)
    customerFacing = any(I.AP[a].get("customer_facing") and apps[a] != "Configure" for a in ids) or \
        (any(I.CUST in I.ST[s]["R"] or I.ST[s]["A"] == I.CUST for s in stepsChanged) if I.CUST else False)
    domains = [dict(id=d["id"], name=d["name"], role="System of record changes" if d["sor"] in ids else "Consumer changes")
               for d in D.get("data_domains") or [] if d["sor"] in ids or any(c in ids for c in d.get("consumers") or [])]
    sups = []
    for a in ids:
        for x in I.appSups[a]:
            if not any(s["sup"] == x["supplier"] for s in sups):
                sups.append(dict(sup=x["supplier"], role=x["role"], app=a))
    for s in sups:
        k = I.K.get(s["sup"])
        if not k:
            continue
        s["contract"], s["end"], s["autoRenew"] = k["id"], k["end"], k["auto_renew"]
        kq = q2n(dateQ(k["end"]))
        if not k["auto_renew"] and apps[s["app"]] != "Configure" and tq is not None and kq is not None and kq <= tq:
            flags.append(_flag("warn", "Contract", js_str((I.SU.get(s["sup"]) or {}).get("name")) + " contract " + k["id"] + " ends " + k["end"] +
                               " without auto-renewal, on or before the target quarter. Renew or extend before committing the work."))
    tier01 = [x for x in direct if x["tier"] <= 1]
    crit = [x for x in direct if x["crit"]]
    CRP = I.PROF.get("criticality") or {}
    if crit:
        txt = (CRP.get("change_flag") or "Changes {n} application{s} supporting critical services: follow change management and assess the risk before release.")
        txt = txt.replace("{n}", str(len(crit)), 1).replace("{s}", "s" if len(crit) > 1 else "", 1)
        flags.append(_flag("info", CRP.get("flag_kind") or "Critical service", txt))
    dr = [x["app"] for x in tier01 if x["change"] != "Configure" and I.RES.get(x["app"]) and re.search(r"Failed|issues|Not tested", I.RES[x["app"]]["dr_result"])]
    if dr:
        sev = "warn" if re.search(r"Failed|Not tested", ",".join(I.RES[a]["dr_result"] for a in dr)) else "info"
        flags.append(_flag(sev, "Resilience", "Tier 0 or 1 applications with open DR issues: " + ", ".join(I.AP[a]["name"] for a in dr) + ". Include a DR test after release."))
    m = 0
    for x in tier01:
        if x["app"] in I.RES:
            m = max(m, I.RES[x["app"]]["rto_hours"])
    rto = m or None
    for x in direct:
        if x["time"] in ("Migrate", "Eliminate") and x["change"] in ("New", "Enhance", "Integrate"):
            flags.append(_flag("warn", "Sunset", "Invests in " + I.AP[x["app"]]["name"] + ", which is rated " + x["time"] + ". Check the work is still worth doing on this platform."))
    drivers = f.get("drivers") or []
    bd = []
    PGN = (D.get("programme") or {}).get("name") or "the programme"
    for k, b in I.BD.items():
        hit = [a for a in b["apps"] if a in ids and apps[a] != "Configure"]
        if not hit:
            continue
        ps = None
        for p in I.PH:
            if not ps and (b.get("phase") or "").lower().startswith(p[0].split(" (")[0].lower()):
                ps = p[1]
        bd.append(dict(id=b["id"], title=b["title"], phase=b.get("phase"), apps=hit))
        if b["id"] not in drivers and tq is not None and ps and tq >= q2n(ps) - 2:
            flags.append(_flag("warn", "Programme", "Change twice risk: " + ", ".join(I.AP[a]["name"] for a in hit) + " " + ("are" if len(hit) > 1 else "is") + " in " +
                               b["id"] + " " + b["title"] + " (" + js_str(b.get("phase")) + "). Align with " + PGN + " before building."))
    reqs = [d for d in drivers if d in I.REQ]
    related = []
    for k, r in I.REQ.items():
        if k in reqs:
            continue
        if any(a in ids and apps[a] != "Configure" for a in r["q"]["apps"]):
            related.append(k)
    for k in reqs:
        r = I.REQ[k]
        dd = r["reg"].get("dates") or {}
        dl = dd.get(r["q"].get("deadline")) or dd.get(r["reg"].get("main_date") or "general")
        if not dl:
            ds = sorted(v for v in dd.values() if isinstance(v, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", v))
            dl = ds[-1] if ds else None
        dq = q2n(dateQ(dl))
        if tq is not None and dq is not None and tq > dq:
            flags.append(_flag("crit", "Deadline", k + " must be in place by " + dl + "; the target " + f["target"] + " is later."))
        elif tq is not None and dq is not None and dq - tq <= 1 and f.get("status") != "Done":
            flags.append(_flag("warn", "Deadline", k + " deadline " + dl + " leaves less than two quarters of margin."))
    if related:
        flags.append(_flag("info", "Regulation", "Also changes applications named in " + ", ".join(related) + ". Check the design meets those requirements too, to avoid rework."))
    inits = [d for d in drivers if d in I.SI]
    relInits = [k for k, s in I.SI.items() if k not in inits and any(a in ids and apps[a] != "Configure" for a in s["apps"])]
    contention = []
    for o in others or []:
        if o["id"] == f.get("id") or o.get("status") == "Done":
            continue
        oq = q2n(o.get("target"))
        if tq is None or oq is None or abs(oq - tq) > 1:
            continue
        shared = [a for a in (o.get("apps") or {}) if a in ids and apps[a] != "Configure" and o["apps"][a] != "Configure"]
        if shared:
            contention.append(dict(feature=o["id"], name=o["name"], target=o["target"], apps=shared))
    if len(contention) >= 2:
        flags.append(_flag("warn", "Contention", str(len(contention)) + " other features change the same applications within one quarter. Plan releases and testing together."))
    for dep in f.get("depends") or []:
        o = next((x for x in others or [] if x["id"] == dep), None)
        if not o:
            continue
        oq = q2n(o.get("target"))
        if tq is not None and oq is not None and oq >= tq:
            flags.append(_flag("crit", "Sequence", "Depends on " + o["id"] + " " + o["name"] + ", which is planned for " + o["target"] + ", the same quarter or later."))
    for n in f.get("new_ifs") or []:
        if n["source"] not in I.AP or n["target"] not in I.AP:
            continue
        flags.append(_flag("info", "Integration", "New integration: " + I.AP[n["source"]]["name"] + " to " + I.AP[n["target"]]["name"] + " (" + n["data"] + "). Add it to the interface catalogue when built."))
    s1 = 0
    for x in direct:
        tw = TIER_W[x["tier"]] if isinstance(x["tier"], int) and 0 <= x["tier"] < len(TIER_W) else 0
        s1 = s1 + (tw or 1) * (CHANGE_W.get(x["change"]) or 1)
    s2 = 0
    for k in partners:
        s2 = s2 + (1.5 if partners[k]["action"] == "Rework interface" else 0.4)
    score = s1 + s2 + len(journeys) * 1.5 + len(crit) * 2 + len(retrain) * 0.5 + (3 if customerFacing else 0) + len(f.get("new_ifs") or []) * 2
    score = js_round(score)
    TH = (D.get("meta") or {}).get("change_thresholds") or [15, 30, 50]
    level = "Critical" if score >= TH[2] else "High" if score >= TH[1] else "Medium" if score >= TH[0] else "Low"
    order = {"crit": 0, "warn": 1, "info": 2}
    flags.sort(key=lambda g: order[g["sev"]])
    return dict(direct=direct, partners=list(partners.values()), ifsRework=ifsRework, ifsTest=ifsTest, platforms=platforms,
                caps3=caps3, caps2=caps2, stepsChanged=stepsChanged, stepsTouched=stepsTouched, journeys=journeys, cvs=cvs, procs=procs,
                retrain=retrain, inform=inform, techOwners=techOwners, customerFacing=customerFacing, domains=domains, sups=sups,
                tier01=[x["app"] for x in tier01], crit=[x["app"] for x in crit], rto=rto, drIssues=dr,
                reqs=reqs, relatedReqs=related, inits=inits, relatedInits=relInits, prog=bd, contention=contention,
                flags=flags, score=score, level=level)


def run_epic(D, ep, features):
    fs = [f for f in features if f["epic"] == ep["id"]]
    merged = dict(id=ep["id"], name=ep["name"], apps={}, caps=[], steps=[], new_ifs=[], drivers=ep.get("drivers") or [], depends=[], target=None, status=None)
    for f in fs:
        for a, c in f["apps"].items():
            p = merged["apps"].get(a)
            if not p or (CHANGE_W.get(c) or 0) > (CHANGE_W.get(p) or 0):
                merged["apps"][a] = c
        merged["caps"] = uniq(merged["caps"] + f["caps"])
        merged["steps"] = uniq(merged["steps"] + f["steps"])
        merged["new_ifs"] = merged["new_ifs"] + (f.get("new_ifs") or [])
    targets = sorted(f["target"] for f in fs if f.get("target"))
    merged["target"] = targets[-1] if targets else None
    r = run_feature(D, merged, [])
    r["features"] = [f["id"] for f in fs]
    r["first"] = targets[0] if targets else None
    r["last"] = merged["target"]
    r["flags"] = []
    for f in fs:
        for x in run_feature(D, f, features)["flags"]:
            if x["sev"] != "info":
                r["flags"].append(dict(sev=x["sev"], kind=x["kind"], text=f["id"] + ": " + x["text"]))
    return r


# ---------------------------------------------------------------- results for the Excel (same shape as compute_scenarios.js)
def compute(D):
    out = []
    for sc in D["example_scenarios"]:
        r = run_scenario(D, sc)
        T = TYPES[sc["type"]]
        out.append(dict(id=sc["id"], name=sc["name"], type=T["label"], disruptive=T["disruptive"], likelihood=sc.get("likelihood") or None,
                        level=r["level"], risk=risk_rating(r["level"], sc["likelihood"]) if sc.get("likelihood") and T["disruptive"] else "",
                        primary=len(r["primary"]), degraded=len(r["degraded"]) + len(r["atRisk"]), crit=r["crit"], tier0=r["tier0"],
                        journeys=len(r["journeys"]), steps=len(r["steps"]), caps=len(r["caps"]), procs=len(r["procs"]), ifs=len(r["ifs"]),
                        rto=r["slowestRto"]["hours"] if r["slowestRto"] else None, cost_at_stake=js_fixed2(r["costAtStake"]), cost_delta=js_fixed2(r["costDelta"]),
                        reqs=len(r["reqs"]), effort=r["effort"],
                        apps=[dict(app=a, effect="Down" if a in r["down"] else "Changes" if a in r["changed"] else "Degraded" if a in r["degraded"] else "At risk",
                                   reason=r["down"].get(a) or r["changed"].get(a) or r["degraded"].get(a) or r["atRisk"].get(a)) for a in r["all"]],
                        description=sc.get("description") or "", mitigation=sc.get("mitigation") or ""))
    fo = []
    for f in D["features"]:
        r = run_feature(D, f, D["features"])
        fo.append(dict(id=f["id"], epic=f["epic"], name=f["name"], status=f["status"], target=f["target"], size=f["size"], owner=f["owner"], level=r["level"], score=r["score"],
                       apps=[x["app"] + " " + x["change"] for x in r["direct"]], partners=[dict(app=p["app"], action=p["action"], ifs=len(p["ifs"])) for p in r["partners"]],
                       journeys=r["journeys"], steps_changed=r["stepsChanged"], steps_touched=len(r["stepsTouched"]), procs=r["procs"], caps3=r["caps3"],
                       retrain=r["retrain"], inform=r["inform"], customer_facing=r["customerFacing"], domains=[d["id"] for d in r["domains"]],
                       sups=[s["sup"] for s in r["sups"]], tier01=r["tier01"], crit=r["crit"], contention=[c["feature"] for c in r["contention"]], flags=r["flags"]))
    eo = []
    for e in D["epics"]:
        r = run_epic(D, e, D["features"])
        eo.append(dict(id=e["id"], level=r["level"], score=r["score"], apps=len(r["direct"]), partners=len(r["partners"]), journeys=len(r["journeys"]),
                       retrain=len(r["retrain"]), first=r["first"], last=r["last"], issues=len(r["flags"])))
    return out, dict(features=fo, epics=eo)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".")
    a = ap.parse_args()
    REPO = os.path.join(os.path.abspath(a.workspace), "repository")
    D = json.load(open(os.path.join(REPO, "data.json"), encoding="utf-8"))
    sc, fr = compute(D)
    json.dump(sc, open(os.path.join(REPO, "scenario_results.json"), "w"), separators=(",", ":"))
    json.dump(fr, open(os.path.join(REPO, "feature_results.json"), "w"), separators=(",", ":"))
    lv = {}
    for x in fr["features"]:
        lv[x["level"]] = lv.get(x["level"], 0) + 1
    print("scenarios", len(sc), " ".join(x["id"] + ":" + x["level"] for x in sc))
    print("features", len(fr["features"]), json.dumps(lv), "(python engine)")
