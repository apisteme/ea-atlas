// ---------- What if? (scenarios and impact)
const SC_SIZE={Low:'Small',Medium:'Medium',High:'Large',Critical:'Very large'};
const SC_LVL_CLS={Low:'ok',Medium:'neutral',High:'warn',Critical:'crit'};
const SC_EFFECT={down:['Down','crit'],degraded:['Degraded','warn'],atRisk:['At risk','warn'],changed:['Changes','neutral']};
const ScStore={mode:'local',items:[],canWrite:true,db:null,user:null,names:{},msg:'',ready:false};
let scDraft=null, scDelArm=null;
function scLoadLocal(){try{ScStore.items=JSON.parse(localStorage.getItem(SKEY+'-scenarios')||'[]')||[]}catch(e){ScStore.items=[]}}
function scSaveLocal(){try{localStorage.setItem(SKEY+'-scenarios',JSON.stringify(ScStore.items))}catch(e){}}
scLoadLocal(); ScStore.ready=true;
(async()=>{
  if(!(window.claude&&typeof window.claude.use==='function')) return;
  let db=null; try{db=await window.claude.use('db')}catch(e){db=null}
  if(!db) return;
  ScStore.db=db; ScStore.mode='shared'; ScStore.items=[]; ScStore.ready=false;
  try{ScStore.user=await window.claude.use('user')}catch(e){ScStore.user=null}
  if(ScStore.user){try{const c=await ScStore.user.can('data.write'); if(c===false) ScStore.canWrite=false}catch(e){}}
  db.collection('scenarios').onSnapshot(snap=>{
    ScStore.items=snap.docs.map(d=>Object.assign({id:d.id},d.data())); ScStore.ready=true; ScStore.msg='';
    scNames(); if(state.view==='scenarios') scRefresh();
  },err=>{ScStore.ready=true; ScStore.msg='Shared scenarios could not be loaded. Examples are still available.'; if(state.view==='scenarios') scRefresh()});
  if(state.view==='scenarios') scRefresh();
})();
async function scNames(){
  const u=ScStore.user; if(!u||!u.profiles) return;
  const ids=[...new Set(ScStore.items.map(x=>x.author).filter(Boolean))]; if(!ids.length) return;
  try{const ps=await u.profiles(ids); ids.forEach(i=>{ScStore.names[i]=(ps[i]&&ps[i].name)||''})}catch(e){}
  if(state.view==='scenarios') scRefresh(true);
}
function scDefault(){return (D.example_scenarios[0]||{}).id||((ScStore.items[0]||{}).id)||''}
function regMain(reg){const d=reg.dates||{};return d[reg.main_date||'general']||Object.values(d).filter(isDate).sort().pop()||''}
function regMainLabel(reg){return (reg.date_labels||{})[reg.main_date||'general']||'Main deadline'}
function regDate(reg,q){const d=reg.dates||{};return d[q.deadline]||regMain(reg)}
function scAll(){return [...ScStore.items.map(x=>Object.assign({saved:true},x)),...D.example_scenarios.map(x=>Object.assign({example:true},x))]}
function scFind(id){return scAll().find(x=>x.id===id)}
function scNewId(){return 'sc-'+Date.now().toString(36)+Math.random().toString(36).slice(2,6)}
async function scSave(sc){
  const body=JSON.parse(JSON.stringify(sc)); delete body.id; delete body.saved; delete body.example;
  body.updatedAt=new Date().toISOString(); if(!body.createdAt) body.createdAt=body.updatedAt;
  if(ScStore.mode==='shared'){
    if(!body.author&&ScStore.user){try{body.author=await ScStore.user.id()}catch(e){}}
    if(!body.author) delete body.author;
    try{await ScStore.db.collection('scenarios').doc(sc.id).set(body); ScStore.msg=''; return true}
    catch(e){
      if(e&&e.code==='invalid_argument'){ScStore.canWrite=false; ScStore.msg='You can view shared scenarios but not save them. Ask the dashboard owner for Contributor access.'}
      else if(e&&e.code==='quota_exceeded') ScStore.msg='Scenario storage is full. Delete scenarios you no longer need, then save again.';
      else ScStore.msg='The scenario was not saved. Check your connection and try again.';
      return false;
    }
  }
  const i=ScStore.items.findIndex(x=>x.id===sc.id); const rec=Object.assign({id:sc.id},body);
  if(i>=0) ScStore.items[i]=rec; else ScStore.items.push(rec); scSaveLocal(); return true;
}
async function scDelete(id){
  if(ScStore.mode==='shared'){try{await ScStore.db.collection('scenarios').doc(id).delete(); return true}catch(e){ScStore.msg='The scenario was not deleted. Try again.'; return false}}
  ScStore.items=ScStore.items.filter(x=>x.id!==id); scSaveLocal(); return true;
}
function scRun(sc){return ScenarioEngine.run(D,sc)}
function scLevelPill(sc,r){
  const T=ScenarioEngine.TYPES[sc.type]||{};
  if(!T.disruptive) return pill('Change size: '+SC_SIZE[r.level],SC_LVL_CLS[r.level]);
  return pill('Impact: '+r.level,SC_LVL_CLS[r.level]);
}
function scRiskPill(sc,r){
  const T=ScenarioEngine.TYPES[sc.type]||{}; if(!T.disruptive||!sc.likelihood) return '';
  const rr=ScenarioEngine.riskRating(r.level,sc.likelihood);
  return pill('Likelihood: '+ScenarioEngine.LIKELIHOOD[sc.likelihood],'neutral')+pill('Risk: '+rr,SC_LVL_CLS[rr]);
}
function scTargetLabel(sc){
  const t=sc.targets||[];
  if(sc.type==='regulatory_change'){const reg=(D.regulations||[]).find(r=>r.id===sc.regulation)||(D.regulations||[])[0];return reg?(reg.name+(t.length?` · ${t.length} of ${reg.requirements.length} requirements`:` · all ${reg.requirements.length} requirements`)):''}
  if(sc.type==='dc_loss') return t.map(x=>(D.data_centres.find(d=>d.id===x)||{}).name||x).join(', ');
  if(sc.type==='supplier_failure'||sc.type==='price_change') return t.map(x=>SU[x]?SU[x].name:x).join(', ')+(sc.type==='price_change'?` · ${sc.pct>0?'+':''}${sc.pct||0}%`:'');
  return t.map(x=>AP[x]?AP[x].name:x).join(', ');
}

function scenarios(){
  const tab=state.scTab||'library';
  const modeNote=ScStore.mode==='shared'
    ?`Saved scenarios are shared with everyone who can open this dashboard.${ScStore.canWrite?'':' You can view them but not save.'}`
    :'Saved scenarios are kept in this browser only. They are not shared with others.';
  $('#view').innerHTML=`<div class="filters" style="align-items:center;justify-content:space-between">
     <div class="seg" role="group" aria-label="Scenario view"><button data-sctab="library" aria-pressed="${tab==='library'}">Scenarios</button><button data-sctab="compare" aria-pressed="${tab==='compare'}">Compare</button></div>
     <span class="muted" style="font-size:12.5px;flex:1;min-width:200px">${esc(modeNote)}</span>
     ${ScStore.canWrite?'<button class="btn" data-scnew="1">New scenario</button>':''}</div>
   <div id="sc-msg">${ScStore.msg?`<div class="callout" style="margin-bottom:12px">${esc(ScStore.msg)}</div>`:''}</div>
   <div id="sc-body"></div>`;
  if(tab==='compare') scCompare(); else scLibrary();
}
function scRefresh(listOnly){
  if(state.view!=='scenarios') return;
  const m=document.getElementById('sc-msg'); if(m) m.innerHTML=ScStore.msg?`<div class="callout" style="margin-bottom:12px">${esc(ScStore.msg)}</div>`:'';
  if((state.scTab||'library')==='compare') return scCompare();
  if(scDraft){ scListRender(); return }
  if(listOnly){ scListRender(); return }
  scLibrary();
}
function scLibrary(){
  const body=document.getElementById('sc-body'); if(!body) return;
  body.innerHTML=`<div class="sc-wrap"><aside class="sc-list" id="sc-list"></aside><div class="sc-main" id="sc-main"></div></div>`;
  scListRender();
  if(scDraft) scEditor(); else scShow(state.scSel&&scFind(state.scSel)?state.scSel:scDefault());
}
function scListRender(){
  const el=document.getElementById('sc-list'); if(!el) return;
  const sel=scDraft?scDraft.id:state.scSel;
  const item=sc=>{const r=scRun(sc);const by=sc.author&&ScStore.names[sc.author]?` · ${esc(ScStore.names[sc.author])}`:'';
    return `<button class="sc-item ${sel===sc.id?'on':''}" data-scsel="${esc(sc.id)}"><span class="sc-item-t">${esc(sc.name||'Untitled scenario')}</span>
      <span class="sc-item-m"><i class="dot s-${SC_LVL_CLS[r.level]}"></i>${esc((ScenarioEngine.TYPES[sc.type]||{}).label||'')}${by}</span></button>`};
  const saved=ScStore.items.map(x=>Object.assign({saved:true},x)).sort((a,b)=>String(b.updatedAt||'').localeCompare(String(a.updatedAt||'')));
  const isNew=scDraft&&!ScStore.items.some(x=>x.id===scDraft.id);
  el.innerHTML=(isNew?`<h4>Editing</h4><button class="sc-item on draft" data-scfocus="1"><span class="sc-item-t">${esc(scDraft.name||'New scenario')}</span><span class="sc-item-m">Not saved yet</span></button>`:'')+`<h4${isNew?' style="margin-top:14px"':''}>Saved <code>${ScStore.ready?saved.length:'…'}</code></h4>
    ${!ScStore.ready?'<p class="empty">Loading shared scenarios…</p>':saved.length?saved.map(item).join(''):`<p class="empty">No saved scenarios yet. ${ScStore.canWrite?'Use New scenario, or open an example and choose Duplicate and edit.':''}</p>`}
    <h4 style="margin-top:14px">Examples <code>${D.example_scenarios.length}</code></h4>${D.example_scenarios.map(x=>item(Object.assign({example:true},x))).join('')}`;
}
function scShow(id){
  state.scSel=id; save(); scDraft=null; scDelArm=null;
  const sc=scFind(id); const main=document.getElementById('sc-main'); if(!sc||!main) return;
  const r=scRun(sc);
  const who=sc.author&&ScStore.names[sc.author]?`Created by ${esc(ScStore.names[sc.author])}. `:'';
  const when=sc.updatedAt?`Last updated ${esc(String(sc.updatedAt).slice(0,10))}.`:'';
  main.innerHTML=`<section class="panel sc-head"><div class="sc-head-top"><div style="min-width:0"><div class="k">${sc.example?'Example scenario':'Saved scenario'} · ${esc((ScenarioEngine.TYPES[sc.type]||{}).label||'')}</div>
      <h2 class="sc-title">${esc(sc.name)}</h2><div class="chips">${scLevelPill(sc,r)}${scRiskPill(sc,r)}<span class="pill s-neutral">${esc(scTargetLabel(sc))}</span></div></div>
      <div class="sc-actions">${ScStore.canWrite?(sc.example?`<button class="btn" data-scdup="${esc(sc.id)}">Duplicate and edit</button>`:`<button class="btn" data-scedit="${esc(sc.id)}">Edit</button>`):''}
      <button class="btn ghost" data-sccopy="${esc(sc.id)}">Copy summary</button></div></div>
      ${sc.description?`<p class="sc-desc">${esc(sc.description)}</p>`:''}
      ${sc.mitigation?`<p class="sc-desc"><b>Response:</b> ${esc(sc.mitigation)}</p>`:''}
      ${(who||when)?`<p class="muted" style="font-size:12px;margin:6px 0 0">${who}${when}</p>`:''}</section>
    <div id="sc-impact">${scImpactHTML(sc,r)}</div>`;
  scListRender();
}
function scKpis(sc,r){
  const k=(l,v,s,cls)=>`<div class="kpi ${cls||''}"><label>${l}</label><b>${v}</b><span>${s}</span></div>`;
  const deg=Object.keys(r.degraded).length, risk=Object.keys(r.atRisk).length;
  const jr=`${r.journeys.length} of ${D.value_streams.length} journeys`;
  if(sc.type==='regulatory_change'){
    const reg=D.regulations.find(x=>x.id===r.regulation);
    const sups=[...new Set(r.primary.map(a=>AP[a].vendor))].filter(x=>!SU[x].internal);
    return k('Requirements',r.reqs.length,`${[...new Set(r.reqs.map(i=>reg.requirements.find(q=>q.id===i).area))].length} areas`)+
      k('Applications to change',r.primary.length,`${r.crit} support ${CR.plural}`,'warn')+
      k('Journeys affected',r.journeys.length,`${r.valueStreams} value streams`)+
      k('Processes',r.procs.length,`${r.roles.length} roles in affected steps`)+
      k('Suppliers to engage',sups.length,'primary vendors of affected apps')+
      k('Effort points',r.effort,'S=1, M=3, L=8. Illustrative')+
      (regMain(reg)?k(regMainLabel(reg),regMain(reg).slice(0,7),'deadline (may be an estimate)','crit'):'');
  }
  if(sc.type==='decommission') return k('Applications retired',r.primary.length,`${r.crit} support ${CR.plural}`)+k('Interfaces to rework',r.ifs.length,'flows into or out of retired apps','warn')+k('Dependent applications',deg+risk,'need interface or hosting change')+k('Journeys to redesign',r.journeys.length,`${r.stepsHit.length} steps use the retired apps`)+k('Run cost saved',fmtM(-r.costDelta),'per year once retired, illustrative');
  if(sc.type==='price_change') return k('Annual cost change',(r.costDelta>=0?'+':'')+fmtM(Math.abs(r.costDelta)),`on ${fmtM(r.costAtStake)} current spend`,r.costDelta>0?'crit':'')+k('Applications repriced',r.primary.length,`${r.crit} support ${CR.plural}`)+k('Journeys exposed',r.journeys.length,`${r.valueStreams} value streams`)+k('Contract',(()=>{const kk=D.contracts.find(x=>(sc.targets||[]).includes(x.supplier));return kk?kk.end:'n/a'})(),'term end; notice applies');
  if(sc.type==='dc_loss'&&!(sc.targets||[]).includes(DCP?DCP.id:'')) return k('Lose standby',risk,'in-house applications with no failover site','warn')+k(CR.short+'s exposed',r.critDegraded,`no recovery path while ${(sc.targets||[]).map(x=>(D.data_centres.find(d=>d.id===x)||{}).name||x).join(', ')} is down`,'crit')+k('Journeys exposed',r.journeys.length,`${r.valueStreams} value streams`);
  return k('Applications down',r.primary.length,`${r.tier0} Tier 0 · ${r.crit} ${CR.plural}`,'crit')+
    k('Degraded',deg+risk,'lose a data flow or dependency','warn')+
    k('Journeys hit',r.journeys.length,`of ${D.value_streams.length} · ${r.valueStreams} value streams`)+
    k('Process steps',r.steps.length,`${r.stepsHit.length} directly`)+
    k('Slowest critical RTO',r.slowestRto?r.slowestRto.hours+'h':'n/a',r.slowestRto?esc(AP[r.slowestRto.app].name):'no Tier 0 or 1 app down')+
    k('DR test issues',r.drIssues.length,'among apps that are down',r.drIssues.length?'crit':'')+
    k('Run cost at stake',fmtM(r.costAtStake),'annual, of apps down');
}
function scImpactHTML(sc,r){
  const reg=sc.type==='regulatory_change'?D.regulations.find(x=>x.id===r.regulation):null;
  const effectOf=a=>r.down[a]?'down':r.changed[a]?'changed':r.degraded[a]?'degraded':'atRisk';
  const reasonOf=a=>r.down[a]||r.changed[a]||r.degraded[a]||r.atRisk[a]||'';
  let html=`<div class="grid g-kpi" style="margin-bottom:16px">${scKpis(sc,r)}</div>`;
  if(r.notes.length) html+=r.notes.map(n=>`<div class="callout" style="margin-bottom:12px">${esc(n)}</div>`).join('');
  if(reg){
    const reqs=reg.requirements.filter(q=>r.reqs.includes(q.id));
    const twice=PG?r.primary.filter(a=>{const k=lensKey(AP[a].programme_lens);return k===LENS_ORDER[0]||k===LENS_ORDER[1]}):[];
    const hits={}; reqs.forEach(q=>q.apps.forEach(a=>{hits[a]=(hits[a]||0)+1}));
    const heat=Object.entries(hits).sort((a,b)=>b[1]-a[1]); const mx=heat.length?heat[0][1]:1;
    const sups={}; r.primary.forEach(a=>{const v=AP[a].vendor; if(SU[v].internal) return; (sups[v]=sups[v]||[]).push(a)});
    html+=`<section class="panel" style="margin-bottom:16px"><h2>Timeline</h2><p class="sub">${esc(reg.status||'')} ${esc(reg.date_note||'')}</p>
      <div class="sc-tl">${[...Object.entries(reg.dates||{}).filter(([k,d])=>isDate(d)).map(([k,d])=>[(reg.date_labels||{})[k]||k.replace(/_/g,' '),d]),...(PG&&PG.completion?[[(PG.completion_label||'Programme completion')+' (expected)',PG.completion]]:[])].sort((a,b)=>a[1].localeCompare(b[1])).map(([l,d])=>`<div><b class="mono">${d.slice(0,7)}</b><span>${esc(l)}</span></div>`).join('')}</div>
      ${PG?`<p class="sub" style="margin-top:10px">${twice.length} of the ${r.primary.length} applications that must change for ${esc(reg.short||reg.id)} are also candidates to converge or be decided under ${esc(PNAME)}, so there is a risk of changing them twice.</p>`:''}
      ${twice.length?`<div class="chips">${twice.map(a=>`<button class="chip" data-ent="app:${a}">${esc(AP[a].name)} <code>${esc(lensKey(AP[a].programme_lens))}</code></button>`).join('')}</div>`:''}</section>
    <section class="panel" style="margin-bottom:16px"><h2>Requirements and where they land</h2><p class="sub">${esc(reg.articles_note||'')} Size is an EA estimate.</p>
      <div class="tbl-wrap"><table><thead><tr><th>ID</th><th>Requirement</th><th>Area</th><th>Type</th><th>Size</th><th>Deadline</th><th>Applications</th></tr></thead><tbody>
      ${reqs.map(q=>`<tr><td class="mono" style="white-space:nowrap">${q.id}</td><td style="min-width:240px"><b style="font-weight:600">${esc(q.short)}</b><div class="muted" style="font-size:12px;margin-top:2px">${esc(q.summary)}</div>${q.articles?`<div class="mono muted" style="font-size:11px;margin-top:3px">Articles: ${esc(q.articles)}</div>`:''}</td><td style="font-size:12.5px">${esc(q.area)}</td><td style="font-size:12.5px">${esc(q.kind)}</td><td class="mono">${q.size}</td><td class="mono" style="font-size:12px">${(regDate(reg,q)||'').slice(0,7)}</td><td><div class="chips">${q.apps.map(a=>chip('app',a,AP[a].name,false)).join('')}</div></td></tr>`).join('')}
      </tbody></table></div></section>
    <div class="grid g-2" style="margin-bottom:16px">
      <section class="panel"><h2>Applications by number of requirements</h2><p class="sub">Where the change concentrates. Click for detail.</p>
        <div class="hbars">${heat.map(([a,n])=>`<button class="hbar" data-ent="app:${a}"><span class="nm">${esc(AP[a].name)}</span><span class="trk"><span class="fil" style="display:block;width:${n/mx*100}%;background:var(--${AP[a].crit?'warn':'accent'})"></span></span><span class="v">${n}</span></button>`).join('')}</div>
        <div class="legend"><span><i style="background:var(--warn)"></i>Supports a ${esc(CR.short.toLowerCase())}</span><span><i style="background:var(--accent)"></i>Other</span></div></section>
      <section class="panel"><h2>Suppliers to engage</h2><p class="sub">Primary vendors whose roadmaps and contracts must cover the change.</p>
        <div class="tbl-wrap"><table><tbody>${Object.entries(sups).sort((a,b)=>b[1].length-a[1].length).map(([s,as])=>`<tr data-ent="sup:${s}"><td><b style="font-weight:600">${esc(SU[s].name)}</b><div class="muted" style="font-size:12px">${as.map(a=>esc(AP[a].name)).join(', ')}</div></td><td class="num mono">${as.length}</td><td class="mono" style="font-size:12px">${(D.contracts.find(k=>k.supplier===s)||{}).end||''}</td></tr>`).join('')}</tbody></table></div></section>
    </div>`;
  }
  // value streams and journeys
  const byCvs=CVS_ORDER.map(c=>({c,js:D.value_streams.filter(v=>v.parent===c&&r.journeys.includes(v.id))})).filter(x=>x.js.length);
  if(byCvs.length) html+=`<section class="panel" style="margin-bottom:16px"><h2>Value streams and journeys</h2><p class="sub">Steps affected out of the journey's total. Click a journey for its process map.</p>
    <div class="sc-vs">${byCvs.map(x=>`<div><h3>${esc(CVS[x.c].name)}</h3>${x.js.map(v=>{const all=D.steps.filter(s=>s.vs===v.id);const hit=all.filter(s=>r.steps.includes(s.id));const dir=all.filter(s=>r.stepsHit.includes(s.id));
      return `<button class="sc-j" data-pmap="${v.id}"><span>${esc(v.name)}</span><span class="sc-steps">${all.map(s=>`<i class="${r.stepsHit.includes(s.id)?'h':r.steps.includes(s.id)?'d':''}" title="${esc(s.name)}"></i>`).join('')}</span><em>${dir.length}/${all.length}</em></button>`}).join('')}</div>`).join('')}</div>
    <div class="legend"><span><i style="background:var(--crit)"></i>Step uses an application that is ${sc.type==='regulatory_change'||sc.type==='decommission'||sc.type==='price_change'?'changing':'down'}</span><span><i style="background:var(--warn)"></i>Step uses a degraded or at-risk application</span><span><i style="background:var(--line)"></i>Not affected</span></div></section>`;
  // applications table
  const rows=r.all.slice().sort((a,b)=>{const o={down:0,changed:0,degraded:1,atRisk:2};return o[effectOf(a)]-o[effectOf(b)]||AP[a].tier_n-AP[b].tier_n});
  html+=`<section class="panel" style="margin-bottom:16px"><h2>Applications · ${rows.length}</h2><p class="sub">Why each application is affected. Click for full detail.</p>
    <div class="tbl-wrap"><table><thead><tr><th>Effect</th><th>Application</th><th>Reason</th><th>Tier</th><th class="num">RTO</th><th>DR result</th></tr></thead><tbody>
    ${rows.map(a=>{const e=SC_EFFECT[effectOf(a)],rs=RES[a];return `<tr data-ent="app:${a}"><td>${pill(e[0],e[1])}</td><td><b style="font-weight:600">${esc(AP[a].name)}</b>${AP[a].crit?CRB():''}<div class="muted" style="font-size:12px">${esc(AP[a].product)}</div></td><td style="font-size:12.5px;min-width:200px">${esc(reasonOf(a))}</td><td class="mono">${AP[a].tier.replace('Tier ','T')}</td><td class="num mono">${rs?rs.rto_hours+'h':''}</td><td style="font-size:12px">${rs?esc(rs.dr_result):''}</td></tr>`}).join('')}
    </tbody></table></div></section>`;
  // capabilities / processes / roles
  const capBy={}; r.caps.forEach(c=>{const p=CAP[c].parent;(capBy[p]=capBy[p]||[]).push(c)});
  html+=`<div class="grid g-2" style="margin-bottom:16px"><section class="panel"><h2>Capabilities · ${r.caps.length}</h2><p class="sub">Grouped by capability domain.</p>
    ${L1.filter(l=>capBy[l.id]).map(l=>`<div style="margin-bottom:8px"><div class="mono muted" style="font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;margin-bottom:4px">${esc(l.name)}</div><div class="chips">${capBy[l.id].map(c=>chip('cap',c,CAP[c].name)).join('')}</div></div>`).join('')}</section>
    <section class="panel"><h2>Processes · ${r.procs.length}</h2><div class="chips" style="margin-bottom:14px">${r.procs.map(p=>chip('bp',p,BP[p].name)).join('')||'<span class="empty">None</span>'}</div>
      <h2>Roles in affected steps · ${r.roles.length}</h2><div class="chips" style="margin-bottom:14px">${r.roles.map(x=>chip('role',x,RO[x].name,false)).join('')||'<span class="empty">None</span>'}</div>
      <h2>Suppliers involved · ${r.sups.length}</h2><div class="chips">${r.sups.map(x=>chip('sup',x,SU[x].name,false)).join('')}</div></section></div>`;
  if(reg&&(reg.sources||[]).length) html+=`<p class="muted" style="font-size:12px">Sources: ${reg.sources.map(s=>`<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>`).join(' · ')}</p>`;
  return html;
}

// ---------- editor
function scBlank(){return {id:scNewId(),name:'',type:'app_outage',targets:[],likelihood:3,pct:10,regulation:(D.regulations[0]||{}).id||'',description:'',mitigation:''}}
function scOpenEditor(sc){scDraft=JSON.parse(JSON.stringify(sc)); delete scDraft.saved; delete scDraft.example; scDelArm=null; const m=document.getElementById('sc-main'); if(!m) return scLibrary(); scEditor(); scListRender()}
function scTargetOptions(type){
  const T=ScenarioEngine.TYPES[type].target;
  if(T==='app') return D.apps.slice().sort((a,b)=>a.name.localeCompare(b.name)).map(a=>[a.id,a.name+' · '+a.product]);
  if(T==='platform') return ScenarioEngine.platformIds(D).map(i=>[i,AP[i].name+' · '+AP[i].product]);
  if(T==='sup') return D.suppliers.slice().sort((a,b)=>a.name.localeCompare(b.name)).map(s=>[s.id,s.name]);
  return [];
}
function scTargetsHTML(){
  const d=scDraft, T=ScenarioEngine.TYPES[d.type];
  if(T.target==='dc') return `<div class="chips">${D.data_centres.map(x=>`<label class="chip"><input type="checkbox" data-scdc="${x.id}" ${d.targets.includes(x.id)?'checked':''}> ${esc(x.name)} <code>${esc(x.role)}</code></label>`).join('')}</div>`;
  if(T.target==='requirement'){const reg=D.regulations.find(x=>x.id===d.regulation)||D.regulations[0]; const areas=[...new Set(reg.requirements.map(q=>q.area))];
    if(!reg) return '<p class="empty">No regulation is recorded in the model.</p>';
    return `${D.regulations.length>1?`<label class="sc-f" style="margin-bottom:8px">Regulation<select id="sc-reg">${D.regulations.map(x=>`<option value="${esc(x.id)}" ${x.id===reg.id?'selected':''}>${esc(x.name)}</option>`).join('')}</select></label>`:''}<p class="sub" style="margin:0 0 6px">${esc(reg.name)}. Untick requirements that do not apply to ${esc(ORGS)}. <button class="chip" data-screq="all">Select all</button> <button class="chip" data-screq="none">Clear</button></p>
      <div class="sc-reqs">${areas.map(ar=>`<div><div class="mono muted" style="font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;margin:6px 0 4px">${esc(ar)}</div>${reg.requirements.filter(q=>q.area===ar).map(q=>`<label class="sc-req"><input type="checkbox" data-screqid="${q.id}" ${(!d.targets.length||d.targets.includes(q.id))?'checked':''}> <span><b>${q.id}</b> ${esc(q.short)}</span></label>`).join('')}</div>`).join('')}</div>`}
  const opts=scTargetOptions(d.type).filter(o=>!d.targets.includes(o[0]));
  return `<div class="chips" style="margin-bottom:8px">${d.targets.map(t=>`<span class="chip">${esc(AP[t]?AP[t].name:SU[t]?SU[t].name:t)} <button class="x-mini" data-scrm="${esc(t)}" aria-label="Remove">✕</button></span>`).join('')||'<span class="empty">Nothing selected yet.</span>'}</div>
    <div style="display:flex;gap:8px;flex-wrap:wrap"><select id="sc-add" style="flex:1;min-width:200px"><option value="">Choose ${T.target==='sup'?'a supplier':T.target==='platform'?'a platform':'an application'}…</option>${opts.map(o=>`<option value="${esc(o[0])}">${esc(o[1])}</option>`).join('')}</select><button class="btn ghost" data-scadd="1">Add</button></div>
    ${d.type==='price_change'?`<label class="sc-f" style="margin-top:10px">Price change (%)<input id="sc-pct" type="number" step="5" value="${Number(d.pct)||0}"></label>`:''}`;
}
function scEditor(){
  const d=scDraft, main=document.getElementById('sc-main'); if(!main||!d) return;
  const isSaved=ScStore.items.some(x=>x.id===d.id);
  const T=ScenarioEngine.TYPES[d.type];
  main.innerHTML=`<div class="ed-head" id="sc-edhead" tabindex="-1"><div><div class="k">What if?</div><h2 class="sc-title" style="margin:2px 0 4px">${isSaved?'Edit scenario':esc(d.name)?'New scenario: '+esc(d.name):'New scenario'}</h2>
     <p class="sub" style="margin:0">${isSaved?'Change the details and save.':'Name it, choose the type and what is affected. The impact preview below updates as you go. Nothing is saved until you press Save scenario.'}</p></div>
     <button class="btn ghost" data-sccancel="1">Back to scenarios</button></div>
    <section class="panel sc-form ed-form">
    <label class="sc-f" id="sc-f-name">Name<input id="sc-name" value="${esc(d.name)}" placeholder="e.g. Loss of ${esc(DCP?DCP.name:'the primary data centre')}" maxlength="120"></label>
    <label class="sc-f">Scenario type<select id="sc-type">${Object.entries(ScenarioEngine.TYPES).map(([k,t])=>`<option value="${k}" ${d.type===k?'selected':''}>${esc(t.label)}</option>`).join('')}</select></label>
    <p class="sub" id="sc-help" style="margin:-4px 0 10px">${esc(T.help)}</p>
    <div class="sc-f" id="sc-f-targets"><span>What is affected</span><div id="sc-targets">${scTargetsHTML()}</div></div>
    <label class="sc-f" id="sc-lk-wrap" ${T.disruptive?'':'hidden'}>Likelihood<select id="sc-lk">${[1,2,3,4,5].map(i=>`<option value="${i}" ${Number(d.likelihood)===i?'selected':''}>${i} · ${ScenarioEngine.LIKELIHOOD[i]}</option>`).join('')}</select></label>
    <label class="sc-f">Description<textarea id="sc-desc" rows="2" placeholder="What happens, and why it matters">${esc(d.description)}</textarea></label>
    <label class="sc-f">Response or mitigation<textarea id="sc-mit" rows="2" placeholder="What ${esc(ORGS)} would do">${esc(d.mitigation)}</textarea></label>
    <div id="sc-ready" class="ed-ready" aria-live="polite"></div>
    <p id="sc-formmsg" class="ed-alert" role="alert" hidden></p>
    <div class="sc-actions" style="justify-content:flex-start;margin-top:4px"><button class="btn" data-scsave="1" aria-describedby="sc-ready">Save scenario</button><button class="btn ghost" data-sccancel="1">Cancel</button>
    ${isSaved?`<button class="btn ghost" data-scdel="${esc(d.id)}" style="margin-left:auto;color:var(--crit)">${scDelArm===d.id?'Confirm delete':'Delete'}</button>`:''}</div></section>
    <h2 style="font:600 17px var(--f-display);margin:18px 0 10px">Impact preview</h2><div id="sc-impact"></div>`;
  scPreview();
  edFocus(main,'sc-name');
}
// ---------- Save readiness for the What if? and Change impact editors
// Shows, above the Save button, what still has to be filled in, ticks items off as the user works, and on an early
// Save explains what is missing next to the button and takes the user to the first field that needs attention.
function edReady(px,items,noun){
  const el=document.getElementById(px+'-ready'); if(!el) return;
  const todo=items.filter(x=>!x.ok), a=document.getElementById(px+'-formmsg');
  // After an early Save the red message alone lists what is missing, and updates as fields are filled in.
  if(a&&!a.hidden&&a.dataset.kind==='check'){
    if(todo.length){a.textContent=`This ${noun} cannot be saved yet. ${todo.map(x=>x.label).join('. ')}.`; el.hidden=true; return}
    a.hidden=true;
  }
  el.hidden=false;
  el.classList.toggle('done',!todo.length);
  el.innerHTML=!todo.length?`<span class="ed-ok">Ready to save.</span>`
    :`<b>To save this ${noun}:</b><ul>${items.map(x=>`<li class="${x.ok?'ed-ok':'ed-todo'}">${esc(x.label)}</li>`).join('')}</ul>`;
}
function edAlert(px,text,kind){const a=document.getElementById(px+'-formmsg'); if(!a) return; a.textContent=text||''; a.dataset.kind=kind||'error'; a.hidden=!text}
function edBlockSave(px,items,noun,focusIds){
  const todo=items.filter(x=>!x.ok); if(!todo.length) return true;
  edAlert(px,'x','check'); edReady(px,items,noun);
  const w=document.getElementById(px+'-f-'+todo[0].f), f=document.getElementById(focusIds[todo[0].f]);
  try{(w||f).scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})}catch(e){}
  if(f) try{f.focus({preventScroll:true})}catch(e){f.focus()}
  return false;
}
// What still has to be filled in before a scenario can be saved, shown above the Save button as the user works.
function scReadyItems(d){
  const reg=d.type==='regulatory_change';
  return [{f:'name',label:'Give the scenario a name',ok:!!String(d.name||'').trim()},
    {f:'targets',label:reg?'Select at least one requirement under "What is affected"':'Add at least one item under "What is affected"',
     ok:reg?!d.targets.includes('__none__'):d.targets.filter(x=>x!=='__none__').length>0}];
}
function scReadyRender(){edReady('sc',scDraft?scReadyItems(scDraft):[],'scenario')}
function scPreview(){
  scReadyRender();
  const el=document.getElementById('sc-impact'); if(!el||!scDraft) return;
  if(!scDraft.targets.length&&scDraft.type!=='regulatory_change'){el.innerHTML='<p class="empty">Add at least one item under "What is affected" to see the impact.</p>';return}
  const r=scRun(scDraft);
  el.innerHTML=`<div class="chips" style="margin-bottom:12px">${scLevelPill(scDraft,r)}${scRiskPill(scDraft,r)}</div>`+scImpactHTML(scDraft,r);
}
function scReadForm(){
  const d=scDraft; if(!d) return;
  const g=id=>document.getElementById(id);
  if(g('sc-name')) d.name=g('sc-name').value;
  if(g('sc-desc')) d.description=g('sc-desc').value;
  if(g('sc-mit')) d.mitigation=g('sc-mit').value;
  if(g('sc-lk')) d.likelihood=Number(g('sc-lk').value);
  if(g('sc-reg')) d.regulation=g('sc-reg').value;
  if(g('sc-pct')) d.pct=Number(g('sc-pct').value)||0;
}
function scCopy(id){
  const sc=scFind(id); if(!sc) return; const r=scRun(sc);
  const lines=[sc.name,`Type: ${(ScenarioEngine.TYPES[sc.type]||{}).label}. Affects: ${scTargetLabel(sc)}.`,
    (ScenarioEngine.TYPES[sc.type]||{}).disruptive?`Impact: ${r.level}${sc.likelihood?`. Likelihood: ${ScenarioEngine.LIKELIHOOD[sc.likelihood]}. Risk: ${ScenarioEngine.riskRating(r.level,sc.likelihood)}`:''}.`:`Change size: ${SC_SIZE[r.level]}.`,
    `Applications directly affected: ${r.primary.length} (${r.crit} support ${CR.plural}). Degraded or at risk: ${Object.keys(r.degraded).length+Object.keys(r.atRisk).length}.`,
    `Journeys: ${r.journeys.map(v=>VS[v].name).join('; ')}.`,
    r.slowestRto?`Slowest critical recovery target: ${r.slowestRto.hours} hours (${AP[r.slowestRto.app].name}).`:'',
    r.reqs.length?`Requirements in scope: ${r.reqs.length}. Effort points: ${r.effort}.`:'',
    r.costDelta?`Annual cost effect: ${r.costDelta>0?'+':'-'}${fmtM(Math.abs(r.costDelta))} (illustrative).`:'',
    sc.mitigation?`Response: ${sc.mitigation}`:'',`Source: ${D.meta.dashboard_title||ORGS+' Atlas'} reference model; figures are illustrative unless confirmed.`].filter(Boolean).join('\n');
  const done=()=>{ScStore.msg='Summary copied to the clipboard.'; scRefresh(true); setTimeout(()=>{if(ScStore.msg==='Summary copied to the clipboard.'){ScStore.msg='';scRefresh(true)}},2500)};
  try{navigator.clipboard.writeText(lines).then(done,()=>scCopyFallback(lines))}catch(e){scCopyFallback(lines)}
}
function scCopyFallback(text){
  const m=document.getElementById('sc-msg'); if(!m) return;
  m.innerHTML=`<div class="callout" style="margin-bottom:12px">Copy the summary below.<textarea id="sc-copytxt" rows="6" style="width:100%;margin-top:6px;font:12px var(--f-mono)">${esc(text)}</textarea></div>`;
  const t=document.getElementById('sc-copytxt'); if(t){t.focus();t.select()}
}

// ---------- compare
function scCompare(){
  const body=document.getElementById('sc-body'); if(!body) return;
  const all=scAll().map(sc=>({sc,r:scRun(sc)}));
  const dis=all.filter(x=>(ScenarioEngine.TYPES[x.sc.type]||{}).disruptive&&x.sc.likelihood);
  const chg=all.filter(x=>!(ScenarioEngine.TYPES[x.sc.type]||{}).disruptive);
  const L=ScenarioEngine.LEVELS;
  const cell=(lk,lv)=>{const rr=ScenarioEngine.riskRating(lv,lk);const xs=dis.filter(x=>Number(x.sc.likelihood)===lk&&x.r.level===lv);
    const bg={Low:['ok',10],Medium:['warn',12],High:['warn',26],Critical:['crit',24]}[rr];return `<td class="rm-c" style="background:color-mix(in oklab,var(--${bg[0]}) ${bg[1]}%,var(--surface))">${xs.map(x=>`<button class="chip" data-scgo="${esc(x.sc.id)}" title="${esc(x.sc.name)}">${esc(x.sc.name.length>26?x.sc.name.slice(0,25)+'…':x.sc.name)}</button>`).join('')}</td>`};
  body.innerHTML=`<section class="panel" style="margin-bottom:16px"><h2>Risk matrix</h2><p class="sub">Disruption scenarios placed by likelihood and computed impact. Cell colour is the risk rating. Click a scenario to open it.</p>
    <div class="tbl-wrap"><table class="rm"><thead><tr><th style="width:170px">Likelihood</th>${L.map(l=>`<th style="text-align:center">${l}</th>`).join('')}</tr></thead><tbody>
    ${[5,4,3,2,1].map(lk=>`<tr><th style="text-align:left;white-space:nowrap">${lk} · ${ScenarioEngine.LIKELIHOOD[lk]}</th>${L.map(lv=>cell(lk,lv)).join('')}</tr>`).join('')}</tbody></table></div></section>
   <section class="panel" style="margin-bottom:16px"><h2>Disruption scenarios</h2>
    <div class="tbl-wrap"><table><thead><tr><th>Scenario</th><th>Type</th><th>Impact</th><th>Risk</th><th class="num">Down</th><th class="num">Degraded</th><th class="num">Critical functions</th><th class="num">Journeys</th><th>Slowest RTO</th></tr></thead><tbody>
    ${all.filter(x=>(ScenarioEngine.TYPES[x.sc.type]||{}).disruptive).sort((a,b)=>b.r.score-a.r.score).map(x=>`<tr data-scgo="${esc(x.sc.id)}" style="cursor:pointer"><td><b style="font-weight:600">${esc(x.sc.name)}</b>${x.sc.example?' <span class="mono muted">example</span>':''}</td><td style="font-size:12.5px">${esc(ScenarioEngine.TYPES[x.sc.type].label)}</td><td>${pill(x.r.level,SC_LVL_CLS[x.r.level])}</td><td>${x.sc.likelihood?pill(ScenarioEngine.riskRating(x.r.level,x.sc.likelihood),SC_LVL_CLS[ScenarioEngine.riskRating(x.r.level,x.sc.likelihood)]):''}</td><td class="num mono">${x.r.primary.length}</td><td class="num mono">${Object.keys(x.r.degraded).length+Object.keys(x.r.atRisk).length}</td><td class="num mono">${x.r.crit+x.r.critDegraded}</td><td class="num mono">${x.r.journeys.length}</td><td class="mono">${x.r.slowestRto?x.r.slowestRto.hours+'h':''}</td></tr>`).join('')}</tbody></table></div></section>
   <section class="panel"><h2>Change scenarios</h2>
    <div class="tbl-wrap"><table><thead><tr><th>Scenario</th><th>Type</th><th>Change size</th><th class="num">Apps changed</th><th class="num">Interfaces</th><th class="num">Journeys</th><th class="num">Effort</th><th class="num">Annual cost effect</th></tr></thead><tbody>
    ${chg.sort((a,b)=>b.r.score-a.r.score).map(x=>`<tr data-scgo="${esc(x.sc.id)}" style="cursor:pointer"><td><b style="font-weight:600">${esc(x.sc.name)}</b>${x.sc.example?' <span class="mono muted">example</span>':''}</td><td style="font-size:12.5px">${esc(ScenarioEngine.TYPES[x.sc.type].label)}</td><td>${pill(SC_SIZE[x.r.level],SC_LVL_CLS[x.r.level])}</td><td class="num mono">${x.r.primary.length}</td><td class="num mono">${x.r.ifs.length}</td><td class="num mono">${x.r.journeys.length}</td><td class="num mono">${x.r.effort||''}</td><td class="num mono">${x.r.costDelta?(x.r.costDelta>0?'+':'-')+fmtM(Math.abs(x.r.costDelta)):''}</td></tr>`).join('')}</tbody></table></div></section>`;
}

// ---------- events
document.addEventListener('click',async e=>{
  if(state.view!=='scenarios') return;
  const t=e.target.closest('[data-scfocus],[data-sctab],[data-scnew],[data-scsel],[data-scdup],[data-scedit],[data-sccopy],[data-scadd],[data-scrm],[data-scsave],[data-sccancel],[data-scdel],[data-screq],[data-scgo]');
  if(!t) return;
  e.stopPropagation();
  if(t.dataset.scfocus){return edFocus(document.getElementById('sc-main'),'sc-name')}
  if(t.dataset.sctab){state.scTab=t.dataset.sctab;save();return scenarios()}
  if(t.dataset.scgo){state.scTab='library';state.scSel=t.dataset.scgo;scDraft=null;save();return scenarios()}
  if(t.dataset.scnew){state.scTab='library';save();if((state.scTab)!=='library'||!document.getElementById('sc-main')) scenarios();return scOpenEditor(scBlank())}
  if(t.dataset.scsel){scDraft=null;return scShow(t.dataset.scsel)}
  if(t.dataset.scdup){const sc=scFind(t.dataset.scdup);const c=JSON.parse(JSON.stringify(sc));c.id=scNewId();c.name=sc.name+' (copy)';delete c.author;delete c.createdAt;delete c.updatedAt;return scOpenEditor(c)}
  if(t.dataset.scedit){return scOpenEditor(scFind(t.dataset.scedit))}
  if(t.dataset.sccopy){return scCopy(t.dataset.sccopy)}
  if(t.dataset.scadd){scReadForm();const v=(document.getElementById('sc-add')||{}).value;if(v&&!scDraft.targets.includes(v)){scDraft.targets.push(v)};document.getElementById('sc-targets').innerHTML=scTargetsHTML();return scPreview()}
  if(t.dataset.scrm){scReadForm();scDraft.targets=scDraft.targets.filter(x=>x!==t.dataset.scrm);document.getElementById('sc-targets').innerHTML=scTargetsHTML();return scPreview()}
  if(t.dataset.screq){const reg=D.regulations.find(x=>x.id===scDraft.regulation)||D.regulations[0];scDraft.targets=t.dataset.screq==='all'?[]:['__none__'];document.getElementById('sc-targets').innerHTML=scTargetsHTML();return scPreview()}
  if(t.dataset.sccancel){const id=scDraft&&ScStore.items.some(x=>x.id===scDraft.id)?scDraft.id:(state.scSel||scDefault());scDraft=null;return scShow(scFind(id)?id:scDefault())}
  if(t.dataset.scdel){if(scDelArm!==t.dataset.scdel){scDelArm=t.dataset.scdel;t.textContent='Confirm delete';return}
    const ok=await scDelete(t.dataset.scdel);if(ok){scDraft=null;state.scSel=scDefault();save();scenarios()}else scRefresh(true);return}
  if(t.dataset.scsave){scReadForm();
    if(!edBlockSave('sc',scReadyItems(scDraft),'scenario',{name:'sc-name',targets:'sc-add'})) return;
    t.disabled=true;t.textContent='Saving…';const sc=JSON.parse(JSON.stringify(scDraft));const ok=await scSave(sc);
    if(ok){scDraft=null;state.scSel=sc.id;save();scenarios()}else{t.disabled=false;t.textContent='Save scenario';edAlert('sc',ScStore.msg);scRefresh(true)}return}
},true);
document.addEventListener('change',e=>{
  if(state.view!=='scenarios'||!scDraft) return;
  const id=e.target.id;
  if(id==='sc-type'){scReadForm();scDraft.type=e.target.value;scDraft.targets=[];const T=ScenarioEngine.TYPES[scDraft.type];document.getElementById('sc-help').textContent=T.help;document.getElementById('sc-lk-wrap').hidden=!T.disruptive;document.getElementById('sc-targets').innerHTML=scTargetsHTML();return scPreview()}
  if(e.target.dataset.scdc){scDraft.targets=[...document.querySelectorAll('[data-scdc]')].filter(x=>x.checked).map(x=>x.dataset.scdc);return scPreview()}
  if(e.target.dataset.screqid){const reg=D.regulations.find(x=>x.id===scDraft.regulation)||D.regulations[0];const on=[...document.querySelectorAll('[data-screqid]')].filter(x=>x.checked).map(x=>x.dataset.screqid);scDraft.targets=on.length===reg.requirements.length?[]:on.length?on:['__none__'];return scPreview()}
  if(id==='sc-reg'){scReadForm();scDraft.targets=[];document.getElementById('sc-targets').innerHTML=scTargetsHTML();return scPreview()}
  if(id==='sc-lk'||id==='sc-pct'){scReadForm();return scPreview()}
});
let scInT=null;
document.addEventListener('input',e=>{if(state.view!=='scenarios'||!scDraft) return; if(e.target.id==='sc-name'){scDraft.name=e.target.value; const it=document.querySelector('#sc-list .draft .sc-item-t'); if(it) it.textContent=e.target.value||'New scenario'; scReadyRender()} if(e.target.id==='sc-pct'){clearTimeout(scInT);scInT=setTimeout(()=>{scReadForm();scPreview()},250)}});
