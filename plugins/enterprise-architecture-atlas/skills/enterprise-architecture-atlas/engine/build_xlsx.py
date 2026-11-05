"""Builds the Excel repository from repository/data.json and the engine results.
    python3 build_xlsx.py --workspace path/to/ea-atlas"""
import os, json, argparse, datetime as dt, shutil
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    if os.environ.get("ATLAS_NO_OPENPYXL"):
        raise ImportError("disabled for testing")
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo
    from openpyxl.formatting.rule import CellIsRule, FormulaRule
    WRITER = "openpyxl"
except ImportError:
    from mini_xlsx import Workbook, Font, PatternFill, Alignment, Border, Side, get_column_letter, Table, TableStyleInfo, CellIsRule, FormulaRule
    WRITER = "built-in writer (no openpyxl: plain formatting)"

ap = argparse.ArgumentParser(); ap.add_argument("--workspace", default="."); args = ap.parse_args()
WS = os.path.abspath(args.workspace); REPO = os.path.join(WS, "repository"); OUT = os.path.join(WS, "output"); os.makedirs(OUT, exist_ok=True)
D=lambda x: dt.date.fromisoformat(x) if isinstance(x,str) and len(x)==10 and x[4]=="-" else x
d = json.load(open(os.path.join(REPO, "data.json")))
M = d["meta"]; P = M.get("profile", {}); CR = P.get("criticality", {}); TPR = P.get("third_party", {})
CUR = M.get("currency", {}).get("symbol", "€"); ORG = M.get("short_name", M["organisation"]); VSL = P.get("value_stream_label", "Value stream")
PG = d.get("programme")
ASOF = dt.date.fromisoformat(M["as_of"]); XD = f"DATE({ASOF.year},{ASOF.month},{ASOF.day})"
CRL = CR.get("label", "Critical service"); MAT = TPR.get("material_label", "Critical supplier"); TERMS = TPR.get("terms_label", "Required contract terms")
STDL = P.get("capability_standard", {}).get("ref_label", "Reference model mapping")
PLABEL = (PG or {}).get("lens_label", "Programme lens")
wb = Workbook()
F = "Arial"
HDR = PatternFill("solid", fgColor="1F3A5F")
CONF_FILL = {"Customer-provided": "D6EAD6", "Public": "DCE8F7", "Partly confirmed": "FFF2CC", "Illustrative": "F2F2F2"}
app_name = {a["id"]: a["name"] for a in d["apps"]}
role_name = {r["id"]: r["name"] for r in d["roles"]}
sup_name = {s["id"]: s["name"] for s in d["suppliers"]}
cap_name = {c["id"]: c["name"] for c in d["capabilities"]}
lic_contract = {l["app"]: l["contract"] for l in d["licences"]}

def sheet(title, headers, rows, widths=None, conf_col=None):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for r in rows: ws.append(r)
    for c in ws[1]:
        c.font = Font(name=F, bold=True, color="FFFFFF"); c.fill = HDR
        c.alignment = Alignment(vertical="center", wrap_text=True)
    for row in ws.iter_rows(min_row=2):
        for c in row: c.font = Font(name=F, size=10)
    ws.freeze_panes = "B2"
    for i, h in enumerate(headers, 1):
        w = (widths or {}).get(h) or min(max(len(str(h)) + 2, max((len(str(r[i-1])) for r in rows), default=8) + 2), 48)
        ws.column_dimensions[get_column_letter(i)].width = w
    ref = f"A1:{get_column_letter(len(headers))}{len(rows)+1}"
    t = Table(displayName=title.replace(" ", "_").replace("&", "and"), ref=ref)
    t.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    ws.add_table(t)
    if conf_col:
        col = get_column_letter(headers.index(conf_col) + 1)
        for k, v in CONF_FILL.items():
            ws.conditional_formatting.add(f"{col}2:{col}{len(rows)+1}",
                CellIsRule(operator="equal", formula=[f'"{k}"'], fill=PatternFill("solid", fgColor=v)))
    return ws

# ---------------- README
ws = wb.active; ws.title = "README"
lines = [
 (f"{ORG} Enterprise Architecture Repository", True, 14),
 (f"Organisation: {d['meta']['organisation']}   |   As of: {d['meta']['as_of']}   |   Version {d['meta']['version']} released {d['meta']['release_date']}", False, 10),
 ("See the Change Log tab for what changed in each release, and Change Detail for field-level changes detected automatically.", False, 10),
 ("", False, 10),
 ("Purpose", True, 11),
 ("Single source of truth linking business capabilities, value streams/processes, roles (RACI), applications, suppliers, contracts, licences, support and data domains. Tabs are structured for import into EA tools (Archi, LeanIX, Ardoq, Sparx, ServiceNow APM).", False, 10),
 ("", False, 10),
 ("Confidence key (column 'Confidence' on Applications and Suppliers)", True, 11),
 (f"Customer-provided: supplied or confirmed by {ORG}", False, 10),
 ("Public: confirmed from a public organisation, vendor or partner source (see Ref column)", False, 10),
 ("Partly confirmed: capability is public/confirmed but the specific product or vendor is an assumption", False, 10),
 (f"Illustrative: reference-model placeholder; replace with {ORG} data", False, 10),
 ("", False, 10),
 ("Important", True, 11),
 (d["meta"]["disclaimer"], False, 10),
 ("", False, 10),
 ("Context", True, 11),
] + [("• " + c, False, 10) for c in d["meta"]["context"]] + [
 ("", False, 10),
 ("Metamodel", True, 11),
 (f"{VSL} (" + " · ".join(c["name"] for c in d["customer_value_streams"] if not c.get("cross_cutting")) + ") ► Journey ► Process Step (L3) ◄ performed by (RACI) ► Role; Process Step ► realises ► Capability (L1→L2→L3). Business process hierarchy: Operate / Manage / Support ► L1 process group ► L2 process ► Journeys and Applications", False, 10),
 ("Application ► supports Capability; ► used in Process Step; ► supplied by Supplier (vendor, SI, AMS, hosting)", False, 10),
 ("Supplier ► Contract ► Licence (per application); Application ► Support agreement (resolver, hours, SLA, end of support)", False, 10),
 ("Data Domain ► System of record (Application) ► consumers; Interface: Application → Application", False, 10),
 ("", False, 10),
 ("How to maintain", True, 11),
 ("Edit only the entity tabs. Keep IDs stable (C=capability: Cnn L1, Cnn.nn L2, Cnn.nn.nn L3, CVS=value stream, VS=journey, R=role, A=application, S=supplier, K=contract, L=licence, SP=support, D=data domain, I=interface). Multi-value cells use ';' separators. 'Summary' recalculates from the tables.", False, 10),
 ("Example: to record a confirmed vendor, change Applications!Product/Vendor, set Confidence = 'Customer-provided', and update the matching Licences and Support rows.", False, 10),
]
for i, (t, b, s) in enumerate(lines, 1):
    c = ws.cell(row=i, column=1, value=t); c.font = Font(name=F, bold=b, size=s); c.alignment = Alignment(wrap_text=True, vertical="top")
ws.column_dimensions["A"].width = 140

# ---------------- entity tabs
sheet("Capabilities", ["ID","Name","Level","Parent","Description",STDL,"Strategic importance","Maturity (1-5)","Strategic initiatives","Source"],
      [[c["id"],c["name"],c["level"],c["parent"],c["description"],c.get("std_ref",""),c["importance"],c["maturity"],c.get("strategic_initiatives",0),c["source"]] for c in d["capabilities"]])
cvs_name={c["id"]:c["name"] for c in d["customer_value_streams"]}
sheet((VSL+"s")[:31], ["ID","Value stream","Scope","Owner role ID","Owner role","Journeys","Source","Ref"],
      [[c["id"],c["name"],c["scope"],c["owner"],role_name[c["owner"]],";".join(v["id"] for v in d["value_streams"] if v["parent"]==c["id"]),c["source"],c["ref"]] for c in d["customer_value_streams"]],
      widths={"Scope":60,"Ref":30})
sheet("Journeys", ["ID","Journey",VSL+" ID",VSL,"Process owner","Owner role","Trigger","Outcome","Source"],
      [[v["id"],v["name"],v["parent"],cvs_name[v["parent"]],v["owner"],role_name[v["owner"]],v["trigger"],v["outcome"],v["source"]] for v in d["value_streams"]])
sheet("Process Steps", ["Step ID","Journey","Seq","Step (L3)","Capabilities","Applications","Responsible","Accountable","Consulted","Informed"],
      [[s["id"],s["vs"],s["seq"],s["name"],";".join(s["capabilities"]),";".join(s["apps"]),";".join(s["R"]),s["A"],";".join(s["C"]),";".join(s["I"])] for s in d["steps"]],
      widths={"Step (L3)":44,"Applications":28,"Capabilities":28})
raci=[]
for s in d["steps"]:
    for k in ("R","C","I"):
        for r in s[k]: raci.append([s["id"],s["name"],r,role_name[r],k])
    raci.append([s["id"],s["name"],s["A"],role_name[s["A"]],"A"])
sheet("RACI", ["Step ID","Step","Role ID","Role","RACI"], raci, widths={"Step":44})
_stepn={r["id"]:sum(1 for st in d["steps"] for k in ("R","C","I") if r["id"] in st[k])+sum(1 for st in d["steps"] if st["A"]==r["id"]) for r in d["roles"]}
sheet("Roles", ["ID","Role","Org unit","Role family","Journey steps (RACI)","Processes owned","Processes involved","Apps (business owner)","Apps (technology owner)","Source"],
      [[r["id"],r["name"],r["unit"],r["family"],_stepn[r["id"]],"; ".join(b["id"] for b in d["business_processes"] if b["owner"]==r["id"]),
        "; ".join(b["id"] for b in d["business_processes"] if r["id"] in b.get("roles",[]) and b["owner"]!=r["id"]),
        "; ".join(a["id"] for a in d["apps"] if a["business_owner"]==r["id"]),"; ".join(a["id"] for a in d["apps"] if a.get("tech_owner")==r["id"]),r["source"]] for r in d["roles"]],
      widths={"Processes involved":30,"Apps (business owner)":30,"Apps (technology owner)":30})
sheet("Applications", ["ID","Application","Product","Primary vendor ID","Primary vendor","Category","Lifecycle","TIME","Criticality","Hosting","Data centres","Runs on",
      CRL,"Business owner","Users","Tech health (1-5)","Functional fit (1-5)",PLABEL+" (hypothesis)","Confidence","Source detail","Ref","Technology owner"],
      [[a["id"],a["name"],a["product"],a["vendor"],sup_name[a["vendor"]],a["category"],a["lifecycle"],a["time"],a["tier"],a["hosting"],a["data_centres"],"; ".join(f'{x["app"]} {app_name[x["app"]]} ({x["status"]})' for x in a["runs_on"]),
        "Yes" if a["crit"] else "No",role_name.get(a["business_owner"],""),a["users"],a["tech_health"],a["func_fit"],a.get("programme_lens",""),a["confidence"],a["source"],a["ref"],role_name.get(a.get("tech_owner"),"")] for a in d["apps"]],
      widths={"Product":38,"Ref":30,PLABEL+" (hypothesis)":44}, conf_col="Confidence")
_C3=d.get("capabilities_l3",[])
sheet("Capabilities L3", ["ID","L3 capability","Description","L2 ID","L2 capability","L1 domain","Importance (from L2)","Coverage","App count","Applications","Source"],
      [[c["id"],c["name"],c["description"],c["parent"],cap_name[c["parent"]],cap_name[c["l1"]],c["importance"],c["coverage"],len(c["apps"]),"; ".join(f'{a} {app_name[a]}' for a in c["apps"]),c["source"]] for c in _C3],
      widths={"Description":60,"Applications":50,"L3 capability":36,"L2 capability":32})
sheet("App-Capability L3", ["App ID","Application","L3 ID","L3 capability","L2 ID","L2 capability"],
      [[a,app_name[a],c["id"],c["name"],c["parent"],cap_name[c["parent"]]] for c in _C3 for a in c["apps"]])
sheet("App-Capability", ["App ID","Application","Capability ID","Capability"],
      [[a["id"],a["name"],c,cap_name[c]] for a in d["apps"] for c in a["capabilities"]])
sheet("App-Supplier", ["App ID","Application","Supplier ID","Supplier","Relationship"],
      [[x["app"],app_name[x["app"]],x["supplier"],sup_name[x["supplier"]],x["role"]] for x in d["app_supplier"]])
sheet("Suppliers", ["ID","Supplier","Type","HQ","Delivery location","Tier","Risk rating",MAT,"Exit plan","Confidence","Source detail","Ref"],
      [[s["id"],s["name"],s["type"],s["hq"],s["location"],s["tier"],s["risk"],"Yes" if s["material"] else "No",s["exit_plan"],s["confidence"],s["source"],s["ref"]] for s in d["suppliers"]],
      widths={"Ref":30}, conf_col="Confidence")

# Licences / Support first (Contracts sums from them)
lic_rows=[[l["id"],l["app"],app_name[l["app"]],l["contract"],l["model"],l["metric"],l["entitled"],l["consumed"],None,l["annual_cost_m"],D(l["renewal"]),None] for l in d["licences"]]
wl = sheet("Licences", ["ID","App ID","Application","Contract","Licence model","Metric","Entitled","Consumed","Utilisation",f"Annual licence cost ({CUR}m)","Renewal / term end","Compliance status"], lic_rows)
for r in range(2, len(lic_rows)+2):
    wl[f"I{r}"] = f'=IF(G{r}=0,"",H{r}/G{r})'; wl[f"I{r}"].number_format = "0%"
    wl[f"L{r}"] = f'=IF(G{r}=0,"N/A",IF(I{r}>1,"Over-deployed",IF(I{r}<0.65,"Shelfware risk","Compliant")))'
    wl[f"J{r}"].number_format = '#,##0.00;(#,##0.00);"-"'; wl[f"J{r}"].font = Font(name=F, size=10, color="0000FF")
    for col in "GH": wl[f"{col}{r}"].number_format = "#,##0"; wl[f"{col}{r}"].font = Font(name=F, size=10, color="0000FF")
    wl[f"K{r}"].number_format = "yyyy-mm-dd"
    for col in "IL": wl[f"{col}{r}"].font = Font(name=F, size=10)
sp_rows=[[s["id"],s["app"],app_name[s["app"]],lic_contract.get(s["app"],""),s["model"],s["resolver"],role_name.get(s["owner_role"],""),s["hours"],s["sla_availability"]/100,s["sla_p1"],D(s["end_of_support"]),None,s["version_currency"],s["annual_support_cost_m"]] for s in d["support"]]
wsp = sheet("Support", ["ID","App ID","Application","Contract","Support model","Resolver groups","Support owner","Support hours","Availability SLA","P1 response / resolve","Vendor end of support","Months to EoS","Version currency",f"Annual support cost ({CUR}m)"], sp_rows, widths={"Resolver groups":46})
for r in range(2, len(sp_rows)+2):
    wsp[f"I{r}"].number_format = "0.00%"; wsp[f"K{r}"].number_format = "yyyy-mm-dd"
    wsp[f"L{r}"] = f'=IF(ISNUMBER(K{r}),ROUND((K{r}-{XD})/30.4,0),"")'
    wsp[f"N{r}"].number_format = '#,##0.00;(#,##0.00);"-"'; wsp[f"N{r}"].font = Font(name=F, size=10, color="0000FF")
wsp.conditional_formatting.add(f"L2:L{len(sp_rows)+1}", FormulaRule(formula=[f'AND(ISNUMBER(L2),L2<=12)'], fill=PatternFill("solid", fgColor="F8CBAD")))
k_rows=[[k["id"],k["supplier"],sup_name[k["supplier"]],k["title"],D(k["start"]),D(k["end"]),k["notice_months"],"Yes" if k["auto_renew"] else "No",
         "Yes" if k["change_of_control_clause"] else "No",k["regulatory_terms"],None,None,k["source"]] for k in d["contracts"]]
wk = sheet("Contracts", ["ID","Supplier ID","Supplier","Title","Start","End","Notice (months)","Auto-renew","Change-of-control clause",TERMS,f"Annual value ({CUR}m)","Notice deadline","Source"], k_rows, widths={"Title":40})
for r in range(2, len(k_rows)+2):
    wk[f"K{r}"] = f"=SUMIFS(Licences!J:J,Licences!D:D,A{r})+SUMIFS(Support!N:N,Support!D:D,A{r})"
    wk[f"K{r}"].number_format = '#,##0.00;(#,##0.00);"-"'
    wk[f"E{r}"].number_format = wk[f"F{r}"].number_format = "yyyy-mm-dd"
    wk[f"L{r}"] = f"=EDATE(F{r},-G{r})"; wk[f"L{r}"].number_format = "yyyy-mm-dd"
sheet("Data Domains", ["ID","Data domain","System of record ID","System of record","Consumers","Data steward"],
      [[x["id"],x["name"],x["sor"],app_name[x["sor"]],";".join(x["consumers"]),role_name.get(x.get("steward",""),"")] for x in d["data_domains"]])
sheet("Interfaces", ["ID","Source app","Source","Target app","Target","Data","Protocol","Frequency"],
      [[i["id"],i["source_app"],app_name[i["source_app"]],i["target_app"],app_name[i["target_app"]],i["data"],i["protocol"],i["frequency"]] for i in d["interfaces"]])

bp_name={b["id"]:b["name"] for b in d["business_processes"]}
sheet("Business Processes", ["ID","Process","Level","Category","Parent","Owner role ID","Owner role","Capabilities","Applications","Journeys","Source","Roles involved"],
      [[b["id"],b["name"],b["level"],b["category"],b["parent"],b["owner"],role_name[b["owner"]],";".join(b["capabilities"]),";".join(b["apps"]),";".join(b["journeys"]),b["source"],"; ".join(role_name[r] for r in b.get("roles",[]))] for b in d["business_processes"]],
      widths={"Process":40})
sheet("Process-Application", ["Process ID","Process","Category","App ID","Application"],
      [[b["id"],b["name"],b["category"],a,app_name[a]] for b in d["business_processes"] for a in b["apps"]])
sheet("Data Centres", ["ID","Data centre","Role","Mode","Source"],[[x["id"],x["name"],x["role"],x["mode"],x["source"]] for x in d["data_centres"]])
res_rows=[[r["app"],app_name[r["app"]],next(a["tier"] for a in d["apps"] if a["id"]==r["app"]),"Yes" if next(a["crit"] for a in d["apps"] if a["id"]==r["app"]) else "No",
           r["mode"],r["failover_type"],r["rto_hours"],r["rpo_minutes"],D(r["last_dr_test"]) if r["last_dr_test"] else None,None,r["dr_result"]] for r in d["resilience"]]
wr=sheet("Resilience", ["App ID","Application","Criticality",CRL,"Data centre mode","Failover","RTO target (hours)","RPO target (minutes)","Last DR test","Months since test","DR result"], res_rows, widths={"Data centre mode":40})
for r in range(2,len(res_rows)+2):
    wr[f"I{r}"].number_format="yyyy-mm-dd"
    wr[f"J{r}"]=f'=IF(ISNUMBER(I{r}),ROUND(({XD}-I{r})/30.4,0),"")'
    for col in "GH": wr[f"{col}{r}"].font=Font(name=F,size=10,color="0000FF")
wr.conditional_formatting.add(f"J2:J{len(res_rows)+1}", FormulaRule(formula=['AND(ISNUMBER(J2),J2>12)'], fill=PatternFill("solid", fgColor="F8CBAD")))
sheet("Taxonomy", ["Domain","Element","Level","ID prefix","Definition","Example","Parent"],
      [[x["domain"],x["element"],x["level"],x["prefix"],x["definition"],x["example"],x["parent"]] for x in d["taxonomy"]],widths={"Definition":70,"Example":40})
sheet("Relationships", ["From","Relationship","To"],[[x["source"],x["verb"],x["target"]] for x in d["relationships"]],widths={"To":60})
sheet("Glossary", ["ID","Term","Category","Meaning"],[[x["id"],x["term"],x["category"],x["definition"]] for x in d["glossary"]],widths={"Meaning":90,"Term":34})
import json as _j
SCR=_j.load(open(os.path.join(REPO,"scenario_results.json")))
SIZE={"Low":"Small","Medium":"Medium","High":"Large","Critical":"Very large"}
sheet("Scenarios", ["ID","Scenario","Type","Impact / change size","Likelihood (1-5)","Risk rating","Apps down or changing","Degraded or at risk",CRL+"s","Tier 0","Journeys","Process steps","Capabilities","Processes","Interfaces","Slowest critical RTO (h)",f"Run cost at stake ({CUR}m)",f"Annual cost effect ({CUR}m)","Requirements","Effort points","Description","Response"],
      [[x["id"],x["name"],x["type"],x["level"] if x["disruptive"] else SIZE[x["level"]],x["likelihood"],x["risk"],x["primary"],x["degraded"],x["crit"],x["tier0"],x["journeys"],x["steps"],x["caps"],x["procs"],x["ifs"],x["rto"],x["cost_at_stake"],x["cost_delta"] or None,x["reqs"] or None,x["effort"] or None,x["description"],x["mitigation"]] for x in SCR],
      widths={"Scenario":40,"Description":60,"Response":60})
sheet("Scenario Impacts", ["Scenario ID","Scenario","App ID","Application","Effect","Reason"],
      [[x["id"],x["name"],a["app"],app_name[a["app"]],a["effect"],a["reason"]] for x in SCR for a in x["apps"]],widths={"Reason":70,"Scenario":36})
def _qn(q): y,n=q.split("-Q"); return int(y)*4+int(n)-1
def _dl(reg,q):
    dd=reg.get("dates",{}); v=dd.get(q.get("deadline")) or dd.get(reg.get("main_date","general"))
    if not v: ds=sorted(x for x in dd.values() if isinstance(x,str) and len(x)==10); v=ds[-1] if ds else ""
    return v
def _ready(reg,q):
    fs=[f for f in d.get("features",[]) if q["id"] in f["drivers"]]
    dl=_dl(reg,q)
    if not fs: return "Not planned",fs,None
    if all(f["status"]=="Done" for f in fs): return "Done",fs,None
    last=max((f["target"] for f in fs),key=_qn)
    if not dl: return "On track",fs,last
    dq=int(dl[:4])*4+(int(dl[5:7])-1)//3
    return ("Late" if _qn(last)>dq else "On track"),fs,last
_RQ=[(r,q) for r in d["regulations"] for q in r["requirements"]]
sheet("Regulatory Requirements", ["Regulation","ID","Area","Requirement","Summary","Type","Size","Deadline","Articles","Applications","Capabilities","Processes","Readiness","Planned features","Last target quarter"],
      [[r.get("short",r["id"]),q["id"],q.get("area",""),q["short"],q.get("summary",""),q.get("kind",""),q.get("size",""),D(_dl(r,q)) or None,q.get("articles",""),"; ".join(f'{a} {app_name[a]}' for a in q["apps"]),"; ".join(q["caps"]),"; ".join(q["procs"]),
        _ready(r,q)[0],"; ".join(f'{f["id"]} {f["name"]} ({f["status"]})' for f in _ready(r,q)[1]),_ready(r,q)[2] or ""] for r,q in _RQ] or [["","","","No regulations recorded","","","","","","","","","","",""]],
      widths={"Summary":70,"Applications":50,"Requirement":36,"Planned features":50})
_ws=wb["Regulatory Requirements"]
for _r in range(2,len(_RQ)+2): _ws[f"H{_r}"].number_format="yyyy-mm"
_apm={x["id"]:x for x in d["apps"]}
sheet("Requirement-App", ["Regulation","Requirement ID","Requirement","App ID","Application",CRL]+([PLABEL] if PG else []),
      [[r.get("short",r["id"]),q["id"],q["short"],a,app_name[a],"Yes" if _apm[a]["crit"] else "No"]+([_apm[a].get("programme_lens","")] if PG else []) for r,q in _RQ for a in q["apps"]] or [["","","","","",""]+([""] if PG else [])],widths={PLABEL:50,"Requirement":40})
SGd=d["strategy"]; PIL={p["id"]:p for p in SGd["pillars"]}
_apmap={a["id"]:a for a in d["apps"]}
def _weak(a): return _apmap[a]["time"] in ("Migrate","Eliminate") or _apmap[a]["tech_health"]<3
sheet("Strategy", ["ID","Pillar","Pillar type","Initiative","Evidence","Journeys","Processes","Capabilities","Applications","Weak applications behind it","Alignment","Source"],
      [[i["id"],PIL[i["pillar"]]["name"],PIL[i["pillar"]]["kind"],i["title"],i["evidence"],"; ".join(i["journeys"]),"; ".join(i["procs"]),"; ".join(i["caps"]),"; ".join(f'{a} {app_name[a]}' for a in i["apps"]),
        "; ".join(app_name[a] for a in i["apps"] if _weak(a)),
        ("Watch" if any(_weak(a) and _apmap[a]["tier_n"]<=1 for a in i["apps"]) else "Minor gaps" if any(_weak(a) for a in i["apps"]) else "Aligned"),SGd.get("source","")] for i in SGd["initiatives"]],
      widths={"Evidence":60,"Applications":55,"Initiative":34,"Source":30,"Weak applications behind it":40})
sheet("Strategy-App", ["Initiative ID","Initiative","Pillar","App ID","Application","TIME","Tech health","Criticality","Weak support"],
      [[i["id"],i["title"],PIL[i["pillar"]]["name"],a,app_name[a],_apmap[a]["time"],_apmap[a]["tech_health"],_apmap[a]["tier"],"Yes" if _weak(a) else "No"] for i in SGd["initiatives"] for a in i["apps"]],widths={"Initiative":34})
if PG:
    sheet("Programme Decisions", ["ID","Decision","Criticality","Phase","Applications","Options","EA hypothesis"],
          [[x["id"],x["title"],x["criticality"],x["phase"],"; ".join(f'{a} {app_name[a]}' for a in x["apps"]),x["options"],x["hypothesis"]] for x in PG.get("decisions",[])] or [["","","","","","",""]],
          widths={"Options":60,"EA hypothesis":70,"Applications":40})
    if PG.get("commitments"):
        sheet("Programme Commitments", ["Topic","Stated position (paraphrased)","Source","Architecture implication","Affected applications","Ref"],
              [[x["topic"],x["stated"],x.get("source",""),x["implication"],"; ".join(app_name[a] for a in x["apps"]) or "Portfolio-wide",x.get("ref","")] for x in PG["commitments"]],
              widths={"Stated position (paraphrased)":55,"Architecture implication":70,"Ref":30})
    if PG.get("milestones"):
        sheet("Programme Milestones", ["Date","Milestone","Status","Ref"],[[D(x["date"]),x["label"],x["status"],x.get("ref","")] for x in PG["milestones"]],widths={"Ref":30})

# ---------------- Change portfolio
_FR=_j.load(open(os.path.join(REPO,"feature_results.json"))); _FRf={x["id"]:x for x in _FR["features"]}; _FRe={x["id"]:x for x in _FR["epics"]}
_drvname=lambda x: next((i["title"] for i in d["strategy"]["initiatives"] if i["id"]==x),None) or next((q["short"] for r in d["regulations"] for q in r["requirements"] if q["id"]==x),None) or next((b["title"] for b in (PG or {}).get("decisions",[]) if b["id"]==x),x)
_epn={e["id"]:e["name"] for e in d["epics"]}
sheet("Epics", ["ID","Epic","Serves","Owner","Change impact","Impact score","Features","Applications changed","Integration partners","Journeys","Roles to retrain","First target","Last target","Issues","Summary","Source"],
      [[e["id"],e["name"],"; ".join(f"{x} {_drvname(x)}" for x in e["drivers"]),role_name.get(e["owner"],""),_FRe[e["id"]]["level"],_FRe[e["id"]]["score"],sum(1 for f in d["features"] if f["epic"]==e["id"]),
        _FRe[e["id"]]["apps"],_FRe[e["id"]]["partners"],_FRe[e["id"]]["journeys"],_FRe[e["id"]]["retrain"],_FRe[e["id"]]["first"],_FRe[e["id"]]["last"],_FRe[e["id"]]["issues"],e["summary"],e["source"]] for e in d["epics"]],
      widths={"Summary":60,"Serves":50,"Epic":36})
sheet("Features", ["ID","Feature","Epic","Status","Target quarter","Size","Owner","Serves","Depends on","L3 capabilities","Steps whose way of working changes","Description","Source"],
      [[f["id"],f["name"],_epn.get(f["epic"],""),f["status"],f["target"],f["size"],role_name.get(f["owner"],""),"; ".join(f["drivers"]),"; ".join(f["depends"]),"; ".join(f["caps"]),"; ".join(f["steps"]),f["description"],f["source"]] for f in d["features"]],
      widths={"Feature":40,"Description":60,"L3 capabilities":30})
sheet("Feature-App", ["Feature ID","Feature","App ID","Application","Change type","Tier","TIME",CRL],
      [[f["id"],f["name"],a,app_name[a],c,_apmap[a]["tier"],_apmap[a]["time"],"Yes" if _apmap[a]["crit"] else "No"] for f in d["features"] for a,c in f["apps"].items()])
sheet("Feature Impacts", ["ID","Feature","Status","Target","Change impact","Impact score","Applications changed","Integration partners","Interfaces to rework","Journeys","Steps changed","Steps affected","Processes","Roles to retrain","Roles to inform","Customer facing","Tier 0 or 1 apps",CRL+" apps","Contention with","Blockers","Checks","Issues"],
      [[x["id"],x["name"],x["status"],x["target"],x["level"],x["score"],"; ".join(x["apps"]),len(x["partners"]),sum(1 for p in x["partners"] if p["action"]=="Rework interface"),"; ".join(x["journeys"]),"; ".join(x["steps_changed"]),x["steps_touched"],"; ".join(x["procs"]),
        "; ".join(role_name[r] for r in x["retrain"]),len(x["inform"]),"Yes" if x["customer_facing"] else "No",len(x["tier01"]),len(x["crit"]),"; ".join(x["contention"]),
        sum(1 for g in x["flags"] if g["sev"]=="crit"),sum(1 for g in x["flags"] if g["sev"]=="warn"),"\n".join(f'{g["kind"]}: {g["text"]}' for g in x["flags"])] for x in _FR["features"]],
      widths={"Feature":40,"Issues":90,"Applications changed":45,"Roles to retrain":40})

# ---------------- Change log
_CL=d.get("changelog",[])
sheet("Change Log", ["Version","Date","Title","Source","Type","Action","IDs","Change"],
      [[h["version"],D(h["date"]),h["title"],h["source"],c["type"],c["action"],"; ".join(c.get("ids",[])),c["text"]] for h in _CL for c in h["changes"]],
      widths={"Title":34,"Change":80,"IDs":30,"Source":30})
_det=[[h["version"],h.get("diff_from",""),c["type"],c["id"],c["name"],c["action"],c["field"],c["old"],c["new"]] for h in _CL for c in h.get("diff",[])]
if not _det: _det=[[d["meta"]["version"],(_CL[1]["version"] if len(_CL)>1 else ""),"(none)","","No data changes detected against the previous snapshot","","","",""]]
sheet("Change Detail", ["Version","Compared with","Element type","ID","Name","Action","Field","Old value","New value"], _det,
      widths={"Name":40,"Old value":40,"New value":40})

# ---------------- Summary (formulas)
s = wb.create_sheet("Summary", 1)
s["A1"] = f"Portfolio summary (recalculates from the tabs)   |   Version {d['meta']['version']}, {d['meta']['release_date']}"; s["A1"].font = Font(name=F, bold=True, size=13)
rows = [
 ("Applications", "=COUNTA(Applications!A:A)-1", "0"),
 ("Suppliers", "=COUNTA(Suppliers!A:A)-1", "0"),
 ("L2 capabilities", '=COUNTIF(Capabilities!C:C,2)', "0"),
 ("Process steps (L3)", "=COUNTA('Process Steps'!A:A)-1", "0"),
 (f"Annual licence cost ({CUR}m)", "=SUM(Licences!J:J)", "#,##0.0"),
 (f"Annual support cost ({CUR}m)", "=SUM(Support!N:N)", "#,##0.0"),
 (f"Total run cost ({CUR}m)", "=B7+B8", "#,##0.0"),
 ("Apps: Invest", '=COUNTIF(Applications!H:H,"Invest")', "0"),
 ("Apps: Tolerate", '=COUNTIF(Applications!H:H,"Tolerate")', "0"),
 ("Apps: Migrate", '=COUNTIF(Applications!H:H,"Migrate")', "0"),
 ("Apps: Eliminate", '=COUNTIF(Applications!H:H,"Eliminate")', "0"),
 (f"Apps supporting {CR.get('plural','critical services')}", '=COUNTIF(Applications!M:M,"Yes")', "0"),
 ("Licences over-deployed", '=COUNTIF(Licences!L:L,"Over-deployed")', "0"),
 ("Licences with shelfware risk", '=COUNTIF(Licences!L:L,"Shelfware risk")', "0"),
 ("Apps reaching end of support within 12 months", '=COUNTIFS(Support!L:L,"<=12",Support!L:L,"<>")', "0"),
 ("Contracts ending within 12 months", f'=COUNTIFS(Contracts!F:F,">="&{XD},Contracts!F:F,"<="&EDATE({XD},12))', "0"),
 (f"{MAT} without a tested exit plan", '=COUNTIFS(Suppliers!H:H,"Yes",Suppliers!I:I,"<>Documented, tested*")', "0"),
 ("Apps: Customer-provided", '=COUNTIF(Applications!S:S,"Customer-provided")', "0"),
 ("Apps: Public", '=COUNTIF(Applications!S:S,"Public")', "0"),
 ("Apps: Illustrative", '=COUNTIF(Applications!S:S,"Illustrative")', "0"),
 ("L3 capabilities", "=COUNTA('Capabilities L3'!A:A)-1", "0"),
 ("Change features", "=COUNTA(Features!A:A)-1", "0"),
 ("Features with critical change impact", '=COUNTIF(\'Feature Impacts\'!E:E,"Critical")', "0"),
 ("L3 capabilities with no application (gaps)", "=COUNTIF('Capabilities L3'!H:H,\"Gap\")", "0"),
]
for i, (lab, f, fmt) in enumerate(rows, 3):
    s.cell(row=i, column=1, value=lab).font = Font(name=F, size=10)
    c = s.cell(row=i, column=2, value=f); c.font = Font(name=F, size=10, bold=True); c.number_format = fmt
s.column_dimensions["A"].width = 52; s.column_dimensions["B"].width = 14
s["A29"] = f"All costs are illustrative assumptions unless confirmed (blue inputs on Licences/Support). Replace with {ORG} figures."
s["A29"].font = Font(name=F, italic=True, size=9)

XP=os.path.join(OUT, f"{M.get('file_prefix','Atlas')}_EA_Repository.xlsx"); wb.save(XP); print(XP, "written with", WRITER)
print("saved")
