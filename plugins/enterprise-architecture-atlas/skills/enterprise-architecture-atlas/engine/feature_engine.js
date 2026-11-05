/* Atlas change impact engine. Traces what a change feature (or an epic) touches across the atlas.
   Pure functions over the repository data; used inline by the dashboard and by node for the Excel. */
var FeatureImpact = (function(){
  var CHANGE_W = {Retire:2, Replace:2, New:1.5, Integrate:1.5, Enhance:1, Configure:0.5};
  var CHANGE_TYPES = ['New','Enhance','Configure','Integrate','Replace','Retire'];
  var TIER_W = [8,5,3,1];
  var STATUS = ['Idea','Discovery','Ready','In delivery','Done'];
  function q2n(q){var m=/^(\d{4})-Q([1-4])$/.exec(q||'');return m?(+m[1])*4+(+m[2]-1):null}
  function dateQ(d){var m=/^(\d{4})-(\d{2})/.exec(d||'');return m?m[1]+'-Q'+(Math.floor((+m[2]-1)/3)+1):null}
  function uniq(a){var o=[];a.forEach(function(x){if(x!=null&&o.indexOf(x)<0)o.push(x)});return o}
  function idx(D){
    if (D.__fidx) return D.__fidx;
    var I={AP:{},ST:{},VS:{},RES:{},K:{},SU:{},REQ:{},BD:{},SI:{},C3:{}};
    D.apps.forEach(function(a){I.AP[a.id]=a});
    D.steps.forEach(function(s){I.ST[s.id]=s});
    D.value_streams.forEach(function(v){I.VS[v.id]=v});
    (D.resilience||[]).forEach(function(r){I.RES[r.app]=r});
    D.contracts.forEach(function(k){I.K[k.supplier]=k});
    D.suppliers.forEach(function(s){I.SU[s.id]=s});
    (D.regulations||[]).forEach(function(r){r.requirements.forEach(function(q){I.REQ[q.id]={q:q,reg:r}})});
    ((D.programme||{}).decisions||[]).forEach(function(b){I.BD[b.id]=b});
    I.PH=((D.programme||{}).phases||[]).filter(function(p){return typeof p==='object'&&p.start}).map(function(p){return [p.name,p.start]});
    I.CUST=(D.meta||{}).customer_role||'';
    I.PROF=(D.meta||{}).profile||{};
    ((D.strategy||{}).initiatives||[]).forEach(function(s){I.SI[s.id]=s});
    (D.capabilities_l3||[]).forEach(function(c){I.C3[c.id]=c});
    I.appSteps={}; D.apps.forEach(function(a){I.appSteps[a.id]=[]});
    D.steps.forEach(function(s){s.apps.forEach(function(a){if(I.appSteps[a])I.appSteps[a].push(s.id)})});
    I.appSups={}; D.apps.forEach(function(a){I.appSups[a.id]=[]});
    D.app_supplier.forEach(function(x){if(I.appSups[x.app])I.appSups[x.app].push(x)});
    Object.defineProperty(D,'__fidx',{value:I,enumerable:false});
    return I;
  }
  function run(D, f, others){
    var I=idx(D), flags=[], apps=f.apps||{}, ids=Object.keys(apps).filter(function(a){return I.AP[a]});
    var tq=q2n(f.target);
    // applications changed and partners
    var direct=ids.map(function(a){var x=I.AP[a];return {app:a,change:apps[a],tier:x.tier_n,crit:x.crit,time:x.time}});
    var partners={}, ifsRework=[], ifsTest=[];
    D.interfaces.forEach(function(i){
      var s=ids.indexOf(i.source_app)>=0, t=ids.indexOf(i.target_app)>=0;
      if(!(s||t)||(s&&t)) { if(s&&t) ifsTest.push(i.id); return; }
      var me=s?i.source_app:i.target_app, other=s?i.target_app:i.source_app, ct=apps[me];
      var rework=(ct==='Replace'||ct==='Retire');
      (rework?ifsRework:ifsTest).push(i.id);
      var p=partners[other]||(partners[other]={app:other,action:'Regression test',ifs:[]});
      if(rework) p.action='Rework interface'; p.ifs.push(i.id);
    });
    var platforms=uniq(ids.reduce(function(acc,a){return acc.concat((I.AP[a].runs_on||[]).map(function(r){return r.app}))},[])).filter(function(p){return ids.indexOf(p)<0});
    // business
    var caps3=(f.caps||[]).filter(function(c){return I.C3[c]});
    var caps2=uniq(caps3.map(function(c){return I.C3[c].parent}));
    var stepsChanged=(f.steps||[]).filter(function(s){return I.ST[s]});
    var stepsTouched=uniq(ids.reduce(function(acc,a){return acc.concat(apps[a]==='Configure'?[]:I.appSteps[a])},[])).filter(function(s){return stepsChanged.indexOf(s)<0});
    var journeys=uniq(stepsChanged.concat(stepsTouched).map(function(s){return I.ST[s].vs}));
    var cvs=uniq(journeys.map(function(v){return I.VS[v].parent}));
    var procs=D.business_processes.filter(function(b){return b.level===2&&b.apps.some(function(a){return ids.indexOf(a)>=0})}).map(function(b){return b.id});
    // people
    var retrain=uniq(stepsChanged.reduce(function(acc,s){var t=I.ST[s];return acc.concat(t.R,[t.A])},[]));
    var inform=uniq(stepsTouched.reduce(function(acc,s){var t=I.ST[s];return acc.concat(t.R,[t.A])},[])).filter(function(r){return retrain.indexOf(r)<0});
    var techOwners=uniq(ids.map(function(a){return I.AP[a].tech_owner}));
    var customerFacing=ids.some(function(a){return I.AP[a].customer_facing&&apps[a]!=='Configure'})||(I.CUST?stepsChanged.some(function(s){return I.ST[s].R.indexOf(I.CUST)>=0||I.ST[s].A===I.CUST}):false);
    // data
    var domains=(D.data_domains||[]).filter(function(d){return ids.indexOf(d.sor)>=0||(d.consumers||[]).some(function(c){return ids.indexOf(c)>=0})}).map(function(d){return {id:d.id,name:d.name,role:ids.indexOf(d.sor)>=0?'System of record changes':'Consumer changes'}});
    // suppliers and contracts
    var sups=[]; ids.forEach(function(a){I.appSups[a].forEach(function(x){if(!sups.some(function(s){return s.sup===x.supplier}))sups.push({sup:x.supplier,role:x.role,app:a})})});
    sups.forEach(function(s){var k=I.K[s.sup]; if(!k) return; s.contract=k.id; s.end=k.end; s.autoRenew=k.auto_renew;
      var kq=q2n(dateQ(k.end)); if(!k.auto_renew&&apps[s.app]!=='Configure'&&tq!=null&&kq!=null&&kq<=tq) flags.push({sev:'warn',kind:'Contract',text:(I.SU[s.sup]||{}).name+' contract '+k.id+' ends '+k.end+' without auto-renewal, on or before the target quarter. Renew or extend before committing the work.'});});
    // risk and resilience
    var tier01=direct.filter(function(x){return x.tier<=1}), crit=direct.filter(function(x){return x.crit});
    var CRP=I.PROF.criticality||{}; if(crit.length) flags.push({sev:'info',kind:CRP.flag_kind||'Critical service',text:(CRP.change_flag||'Changes {n} application{s} supporting critical services: follow change management and assess the risk before release.').replace('{n}',crit.length).replace('{s}',crit.length>1?'s':'')});
    var dr=tier01.filter(function(x){var r=I.RES[x.app];return x.change!=='Configure'&&r&&/Failed|issues|Not tested/.test(r.dr_result)}).map(function(x){return x.app});
    if(dr.length) flags.push({sev:/Failed|Not tested/.test(dr.map(function(a){return I.RES[a].dr_result}).join())?'warn':'info',kind:'Resilience',text:'Tier 0 or 1 applications with open DR issues: '+dr.map(function(a){return I.AP[a].name}).join(', ')+'. Include a DR test after release.'});
    var rto=tier01.filter(function(x){return I.RES[x.app]}).reduce(function(m,x){return Math.max(m,I.RES[x.app].rto_hours)},0)||null;
    // sunset apps
    direct.forEach(function(x){ if((x.time==='Migrate'||x.time==='Eliminate')&&['New','Enhance','Integrate'].indexOf(x.change)>=0)
      flags.push({sev:'warn',kind:'Sunset',text:'Invests in '+I.AP[x.app].name+', which is rated '+x.time+'. Check the work is still worth doing on this platform.'}); });
    // programme change twice
    var drivers=f.drivers||[], bd=[], PGN=(D.programme||{}).name||'the programme';
    Object.keys(I.BD).forEach(function(k){var b=I.BD[k]; var hit=b.apps.filter(function(a){return ids.indexOf(a)>=0&&apps[a]!=='Configure'}); if(!hit.length) return;
      var ps=null; I.PH.forEach(function(p){if(!ps&&(b.phase||'').toLowerCase().indexOf(p[0].split(' (')[0].toLowerCase())===0)ps=p[1]}); bd.push({id:b.id,title:b.title,phase:b.phase,apps:hit});
      if(drivers.indexOf(b.id)<0&&tq!=null&&ps&&tq>=q2n(ps)-2) flags.push({sev:'warn',kind:'Programme',text:'Change twice risk: '+hit.map(function(a){return I.AP[a].name}).join(', ')+' '+(hit.length>1?'are':'is')+' in '+b.id+' '+b.title+' ('+b.phase+'). Align with '+PGN+' before building.'}); });
    // regulation
    var reqs=drivers.filter(function(d){return I.REQ[d]}), related=[];
    Object.keys(I.REQ).forEach(function(k){if(reqs.indexOf(k)>=0)return; var q=I.REQ[k].q; if(q.apps.some(function(a){return ids.indexOf(a)>=0&&apps[a]!=='Configure'}))related.push(k)});
    reqs.forEach(function(k){var r=I.REQ[k], dd=r.reg.dates||{}, dl=dd[r.q.deadline]||dd[r.reg.main_date||'general']||Object.keys(dd).map(function(x){return dd[x]}).filter(function(x){return /^\d{4}-\d{2}-\d{2}$/.test(x)}).sort().pop(); var dq=q2n(dateQ(dl));
      if(tq!=null&&dq!=null&&tq>dq) flags.push({sev:'crit',kind:'Deadline',text:k+' must be in place by '+dl+'; the target '+f.target+' is later.'});
      else if(tq!=null&&dq!=null&&dq-tq<=1&&f.status!=='Done') flags.push({sev:'warn',kind:'Deadline',text:k+' deadline '+dl+' leaves less than two quarters of margin.'}); });
    if(related.length) flags.push({sev:'info',kind:'Regulation',text:'Also changes applications named in '+related.join(', ')+'. Check the design meets those requirements too, to avoid rework.'});
    // strategy
    var inits=drivers.filter(function(d){return I.SI[d]});
    var relInits=Object.keys(I.SI).filter(function(k){return inits.indexOf(k)<0&&I.SI[k].apps.some(function(a){return ids.indexOf(a)>=0&&apps[a]!=='Configure'})});
    // portfolio: contention and sequencing
    var contention=[];
    (others||[]).forEach(function(o){ if(o.id===f.id||o.status==='Done') return; var oq=q2n(o.target); if(tq==null||oq==null||Math.abs(oq-tq)>1) return;
      var shared=Object.keys(o.apps||{}).filter(function(a){return ids.indexOf(a)>=0&&apps[a]!=='Configure'&&o.apps[a]!=='Configure'}); if(shared.length) contention.push({feature:o.id,name:o.name,target:o.target,apps:shared}); });
    if(contention.length>=2) flags.push({sev:'warn',kind:'Contention',text:contention.length+' other features change the same applications within one quarter. Plan releases and testing together.'});
    (f.depends||[]).forEach(function(dep){ var o=(others||[]).filter(function(x){return x.id===dep})[0]; if(!o) return; var oq=q2n(o.target);
      if(tq!=null&&oq!=null&&oq>=tq) flags.push({sev:'crit',kind:'Sequence',text:'Depends on '+o.id+' '+o.name+', which is planned for '+o.target+', the same quarter or later.'}); });
    (f.new_ifs||[]).forEach(function(n){ if(!I.AP[n.source]||!I.AP[n.target]) return; flags.push({sev:'info',kind:'Integration',text:'New integration: '+I.AP[n.source].name+' to '+I.AP[n.target].name+' ('+n.data+'). Add it to the interface catalogue when built.'}); });
    // score
    var score=direct.reduce(function(t,x){return t+(TIER_W[x.tier]||1)*(CHANGE_W[x.change]||1)},0)
      +Object.keys(partners).reduce(function(t,k){return t+(partners[k].action==='Rework interface'?1.5:0.4)},0)+journeys.length*1.5+crit.length*2+retrain.length*0.5+(customerFacing?3:0)+(f.new_ifs||[]).length*2;
    score=Math.round(score);
    var TH=((D.meta||{}).change_thresholds)||[15,30,50];
    var level=score>=TH[2]?'Critical':score>=TH[1]?'High':score>=TH[0]?'Medium':'Low';
    var order={crit:0,warn:1,info:2}; flags.sort(function(a,b){return order[a.sev]-order[b.sev]});
    return {direct:direct, partners:Object.keys(partners).map(function(k){return partners[k]}), ifsRework:ifsRework, ifsTest:ifsTest, platforms:platforms,
      caps3:caps3, caps2:caps2, stepsChanged:stepsChanged, stepsTouched:stepsTouched, journeys:journeys, cvs:cvs, procs:procs,
      retrain:retrain, inform:inform, techOwners:techOwners, customerFacing:customerFacing, domains:domains, sups:sups,
      tier01:tier01.map(function(x){return x.app}), crit:crit.map(function(x){return x.app}), rto:rto, drIssues:dr,
      reqs:reqs, relatedReqs:related, inits:inits, relatedInits:relInits, prog:bd, contention:contention,
      flags:flags, score:score, level:level};
  }
  function epic(D, ep, features){
    var fs=features.filter(function(f){return f.epic===ep.id});
    var merged={id:ep.id,name:ep.name,apps:{},caps:[],steps:[],new_ifs:[],drivers:ep.drivers||[],depends:[],target:null,status:null};
    fs.forEach(function(f){Object.keys(f.apps).forEach(function(a){var c=f.apps[a],p=merged.apps[a]; if(!p||(CHANGE_W[c]||0)>(CHANGE_W[p]||0)) merged.apps[a]=c});
      merged.caps=uniq(merged.caps.concat(f.caps)); merged.steps=uniq(merged.steps.concat(f.steps)); merged.new_ifs=merged.new_ifs.concat(f.new_ifs||[])});
    var targets=fs.map(function(f){return f.target}).filter(Boolean).sort();
    merged.target=targets[targets.length-1]||null;
    var r=run(D,merged,[]); r.features=fs.map(function(f){return f.id}); r.first=targets[0]||null; r.last=merged.target;
    r.flags=[]; fs.forEach(function(f){run(D,f,features).flags.forEach(function(x){if(x.sev!=='info')r.flags.push({sev:x.sev,kind:x.kind,text:f.id+': '+x.text})})});
    return r;
  }
  return {run:run, epic:epic, CHANGE_TYPES:CHANGE_TYPES, CHANGE_W:CHANGE_W, STATUS:STATUS, q2n:q2n};
})();
if (typeof module!=='undefined') module.exports = FeatureImpact;
