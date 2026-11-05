// ---------- Change impact (epics and features)
const FT_LVL_CLS={Low:'ok',Medium:'neutral',High:'warn',Critical:'crit'};
const FT_ST_CLS={'Idea':'neutral','Discovery':'neutral','Ready':'ok','In delivery':'warn','Done':'ok'};
const FT_CH_CLS={Retire:'crit',Replace:'crit',New:'warn',Integrate:'warn',Enhance:'neutral',Configure:'ok'};
const FT_SEV={crit:['Blocker','crit'],warn:['Check','warn'],info:['Note','neutral']};
const FT_Q=(()=>{const o=[];for(let y=2026;y<=2028;y++)for(let q=1;q<=4;q++)o.push(y+'-Q'+q);return o})();
const EP=Object.fromEntries((D.epics||[]).map(e=>[e.id,e]));
const FtStore={mode:'local',items:[],canWrite:true,db:null,user:null,msg:'',ready:false};
let ftDraft=null, ftDelArm=null;
function ftLoadLocal(){try{FtStore.items=JSON.parse(localStorage.getItem(SKEY+'-features')||'[]')||[]}catch(e){FtStore.items=[]}}
function ftSaveLocal(){try{localStorage.setItem(SKEY+'-features',JSON.stringify(FtStore.items))}catch(e){}}
ftLoadLocal(); FtStore.ready=true;
(async()=>{
  if(!(window.claude&&typeof window.claude.use==='function')) return;
  let db=null; try{db=await window.claude.use('db')}catch(e){db=null}
  if(!db) return;
  FtStore.db=db; FtStore.mode='shared'; FtStore.items=[]; FtStore.ready=false;
  try{FtStore.user=await window.claude.use('user')}catch(e){FtStore.user=null}
  if(FtStore.user){try{const c=await FtStore.user.can('data.write'); if(c===false) FtStore.canWrite=false}catch(e){}}
  db.collection('features').onSnapshot(snap=>{
    FtStore.items=snap.docs.map(d=>Object.assign({id:d.id},d.data())); FtStore.ready=true; FtStore.msg='';
    if(state.view==='change') ftRefresh();
  },err=>{FtStore.ready=true; FtStore.msg='Shared features could not be loaded. The example backlog is still available.'; if(state.view==='change') ftRefresh()});
})();
function ftAll(){return [...(D.features||[]).map(x=>Object.assign({example:true},x)),...FtStore.items.map(x=>Object.assign({saved:true},x))]}
function ftFind(id){return ftAll().find(x=>x.id===id)}
function ftRun(f){return FeatureImpact.run(D,f,ftAll())}
function ftNewId(){return 'ft-'+Date.now().toString(36)+Math.random().toString(36).slice(2,6)}
async function ftSave(f){
  const body=JSON.parse(JSON.stringify(f)); delete body.id; delete body.saved; delete body.example; delete body.seededFrom;
  body.updatedAt=new Date().toISOString(); if(!body.createdAt) body.createdAt=body.updatedAt;
  if(FtStore.mode==='shared'){
    if(!body.author&&FtStore.user){try{body.author=await FtStore.user.id()}catch(e){}}
    if(!body.author) delete body.author;
    try{await FtStore.db.collection('features').doc(f.id).set(body); FtStore.msg=''; return true}
    catch(e){
      if(e&&e.code==='invalid_argument'){FtStore.canWrite=false; FtStore.msg='You can view shared features but not save them. Ask the dashboard owner for Contributor access.'}
      else if(e&&e.code==='quota_exceeded') FtStore.msg='Storage is full. Delete features you no longer need, then save again.';
      else FtStore.msg='The feature was not saved. Check your connection and try again.';
      return false;
    }
  }
  const i=FtStore.items.findIndex(x=>x.id===f.id); const rec=Object.assign({id:f.id},body);
  if(i>=0) FtStore.items[i]=rec; else FtStore.items.push(rec); ftSaveLocal(); return true;
}
async function ftDelete(id){
  if(FtStore.mode==='shared'){try{await FtStore.db.collection('features').doc(id).delete(); return true}catch(e){FtStore.msg='The feature was not deleted. Try again.'; return false}}
  FtStore.items=FtStore.items.filter(x=>x.id!==id); ftSaveLocal(); return true;
}
const ftDriverName=d=>SI[d]?SI[d].title:((PG&&(PG.decisions||[]).find(x=>x.id===d))||{}).title||((D.regulations.flatMap(r=>r.requirements).find(q=>q.id===d)||{}).short)||d;
function ftDriverChip(d){
  if(SI[d]) return `<button class="chip" data-ent="si:${d}"><code>${d}</code>${esc(SI[d].title)}</button>`;
  if(/^BD/.test(d)) return `<button class="chip" data-dec="${d}"><code>${d}</code>${esc(ftDriverName(d))}</button>`;
  return `<button class="chip" data-ftreq="${d}"><code>${d}</code>${esc(ftDriverName(d))}</button>`;
}
function ftFlagsHTML(flags){
  if(!flags.length) return '<p class="empty">No issues found.</p>';
  return `<ul class="ft-flags">${flags.map(x=>`<li class="ft-flag ${x.sev}"><span class="pill s-${FT_SEV[x.sev][1]}">${FT_SEV[x.sev][0]}</span><span><b>${esc(x.kind)}.</b> ${esc(x.text)}</span></li>`).join('')}</ul>`;
}
function ftKpis(r){
  const crit=r.flags.filter(x=>x.sev==='crit').length, warn=r.flags.filter(x=>x.sev==='warn').length;
  const rew=r.partners.filter(p=>p.action==='Rework interface').length;
  const k=(l,v,s,c)=>`<div class="kpi ${c||''}"><label>${l}</label><b>${v}</b><span>${s}</span></div>`;
  return `<div class="ft-kpis">${k('Change impact',r.level,'score '+r.score,r.level==='Critical'?'crit':r.level==='High'?'warn':'')}
    ${k('Applications changed',r.direct.length,r.tier01.length+' Tier 0 or 1 · '+r.crit.length+' '+CR.short.toLowerCase())}
    ${k('Integration partners',r.partners.length,rew?rew+' interfaces to rework':'regression testing')}
    ${k('Journeys',r.journeys.length,r.stepsChanged.length+(r.stepsChanged.length===1?' step changes':' steps change')+' · '+r.stepsTouched.length+' affected')}
    ${k('People',r.retrain.length+r.inform.length,r.retrain.length+' roles to retrain')}
    ${k('Issues',crit+warn,crit?crit+' blockers':'checks to make',crit?'crit':warn?'warn':'')}</div>`;
}
function ftImpactHTML(f,r){
  const appRows=r.direct.map(x=>`<tr data-ent="app:${x.app}"><td><b style="font-weight:600">${esc(AP[x.app].name)}</b><div class="muted" style="font-size:12px">${esc(AP[x.app].product)}</div><div class="chips" style="margin-top:4px">${pill(x.change,FT_CH_CLS[x.change])}<span class="pill s-neutral">Tier ${x.tier}</span>${time(x.time)}${x.crit?pill(CR.short,'warn'):''}</div></td></tr>`).join('');
  const partRows=r.partners.sort((a,b)=>b.action.localeCompare(a.action)).map(p=>`<tr data-ent="app:${p.app}"><td>${esc(AP[p.app].name)}<div class="muted" style="font-size:12px">${p.ifs.length} interface${p.ifs.length>1?'s':''}</div></td><td style="text-align:right">${pill(p.action,p.action==='Rework interface'?'warn':'neutral')}</td></tr>`).join('');
  const roleChips=ids=>ids.length?`<div class="chips">${ids.map(x=>chip('role',x,RO[x].name,false)).join('')}</div>`:'<p class="empty">None.</p>';
  return `${ftKpis(r)}
  <section class="panel" style="margin-bottom:12px"><h2>What to check before committing</h2>${ftFlagsHTML(r.flags)}</section>
  <div class="ft-grid">
   <section class="panel"><h2>Applications changed</h2><div class="tbl-wrap"><table><tbody>${appRows}</tbody></table></div>
     ${r.platforms.length?`<h4 class="ft-h">Runs on platforms</h4>${appChips(r.platforms)}`:''}</section>
   <section class="panel"><h2>Integration</h2>${partRows?`<div class="tbl-wrap"><table><tbody>${partRows}</tbody></table></div>`:'<p class="empty">No interfaces to other applications.</p>'}
     ${(f.new_ifs||[]).length?`<h4 class="ft-h">New integrations</h4><ul class="ft-ul">${f.new_ifs.map(n=>`<li>${esc(AP[n.source].name)} to ${esc(AP[n.target].name)}: ${esc(n.data)}</li>`).join('')}</ul>`:''}</section>
   <section class="panel"><h2>Business</h2>
     <h4 class="ft-h">Capabilities (L3)</h4>${r.caps3.length?`<div class="chips">${r.caps3.map(c=>chip('cap',c,CAP[c].name)).join('')}</div>`:'<p class="empty">None named.</p>'}
     <h4 class="ft-h">Journeys</h4>${r.journeys.length?`<div class="chips">${r.journeys.map(v=>`<button class="chip" data-pmap="${v}"><code>${v}</code>${esc(VS[v].name)}</button>`).join('')}</div>`:'<p class="empty">No customer journey affected.</p>'}
     ${r.stepsChanged.length?`<h4 class="ft-h">Steps whose way of working changes</h4>${stepChips(r.stepsChanged)}`:''}
     ${r.stepsTouched.length?`<h4 class="ft-h">Steps that use a changed application · ${r.stepsTouched.length}</h4>${stepChips(r.stepsTouched)}`:''}
     <h4 class="ft-h">Business processes</h4>${r.procs.length?`<div class="chips">${r.procs.map(b=>chip('bp',b,BP[b].name)).join('')}</div>`:'<p class="empty">None.</p>'}</section>
   <section class="panel"><h2>People and customers</h2>
     <h4 class="ft-h">Retrain (responsible or accountable for changed steps)</h4>${roleChips(r.retrain)}
     <h4 class="ft-h">Inform (work with a changed application)</h4>${roleChips(r.inform)}
     <h4 class="ft-h">Technology owners</h4>${roleChips(r.techOwners)}
     <h4 class="ft-h">Customers</h4><p style="margin:0;font-size:13px">${r.customerFacing?'Customer facing: plan customer communications, help content and contact centre briefing.':'Not customer facing.'}</p></section>
   <section class="panel"><h2>Data, suppliers and resilience</h2>
     <h4 class="ft-h">Data domains</h4>${r.domains.length?`<ul class="ft-ul">${r.domains.map(d=>`<li><b>${esc(d.name)}</b> <span class="muted">${esc(d.role)}</span></li>`).join('')}</ul>`:'<p class="empty">None.</p>'}
     <h4 class="ft-h">Suppliers to engage</h4>${r.sups.length?`<div class="tbl-wrap"><table><tbody>${r.sups.map(s=>`<tr data-ent="sup:${s.sup}"><td>${esc(SU[s.sup].name)}<div class="muted" style="font-size:12px">${esc(s.role)} · ${esc(AP[s.app].name)}</div></td><td class="mono" style="font-size:12px">${s.end?'ends '+esc(s.end):''}${s.autoRenew?' · auto-renews':''}</td></tr>`).join('')}</tbody></table></div>`:'<p class="empty">None.</p>'}
     <h4 class="ft-h">Resilience</h4><p style="margin:0;font-size:13px">${r.tier01.length?`${r.tier01.length} Tier 0 or 1 application${r.tier01.length>1?'s':''}; slowest RTO ${r.rto||'?'} hours. ${r.drIssues.length?'Open DR issues on '+r.drIssues.map(a=>esc(AP[a].name)).join(', ')+'.':''}`:'No Tier 0 or 1 application changes.'}</p></section>
   <section class="panel"><h2>Strategy, regulation${PG?' and '+esc(PNAME):''}</h2>
     <h4 class="ft-h">Serves</h4>${(f.drivers||[]).length?`<div class="chips">${f.drivers.map(ftDriverChip).join('')}</div>`:'<p class="empty">No driver recorded.</p>'}
     ${r.relatedInits.length?`<h4 class="ft-h">Also touches applications behind</h4><div class="chips">${r.relatedInits.map(ftDriverChip).join('')}</div>`:''}
     ${r.relatedReqs.length?`<h4 class="ft-h">Regulatory requirements on the same applications</h4><div class="chips">${r.relatedReqs.map(ftDriverChip).join('')}</div>`:''}
     ${r.prog.length?`<h4 class="ft-h">${esc(PDEC)}s</h4><div class="chips">${r.prog.map(b=>`<button class="chip" data-dec="${b.id}"><code>${b.id}</code>${esc(b.title)} · ${esc(b.phase)}</button>`).join('')}</div>`:''}</section>
   <section class="panel"><h2>Portfolio</h2>
     <h4 class="ft-h">Other features on the same applications within a quarter</h4>${r.contention.length?`<ul class="ft-ul">${r.contention.map(c=>`<li><button class="linklike" data-ftsel="${esc(c.feature)}">${esc(c.feature.startsWith('ft-')?'':c.feature+' ')}${esc(c.name)}</button> <span class="muted">${esc(c.target)} · ${c.apps.map(a=>esc(AP[a].name)).join(', ')}</span></li>`).join('')}</ul>`:'<p class="empty">None.</p>'}
     <h4 class="ft-h">Depends on</h4>${(f.depends||[]).length?`<ul class="ft-ul">${f.depends.map(d=>{const o=ftFind(d);return o?`<li><button class="linklike" data-ftsel="${esc(d)}">${esc(d)} ${esc(o.name)}</button> <span class="muted">${esc(o.target)} · ${esc(o.status)}</span></li>`:''}).join('')}</ul>`:'<p class="empty">No dependencies recorded.</p>'}</section>
  </div>`;
}
function ftHead(f,r,epicMode){
  const e=EP[f.epic];
  return `<div class="sc-head"><div class="sc-head-top"><div><div class="k">${epicMode?'Epic':'Feature'} · ${esc(f.id.startsWith('ft-')?'saved':f.id)}${e&&!epicMode?' · '+esc(e.name):''}</div>
    <h2 class="sc-title">${esc(f.name)}</h2>
    <div class="chips">${epicMode?`<span class="pill s-neutral">${r.features.length} features</span><span class="pill s-neutral">${esc(r.first||'')} to ${esc(r.last||'')}</span>`:`${pill(f.status,FT_ST_CLS[f.status])}<span class="pill s-neutral">Target ${esc(f.target)}</span><span class="pill s-neutral">Size ${esc(f.size)}</span>`}${pill('Change impact: '+r.level,FT_LVL_CLS[r.level])}${f.owner&&RO[f.owner]?chip('role',f.owner,RO[f.owner].name,false):''}${f.example?conf('Illustrative'):''}</div></div>
    <div class="sc-actions">${epicMode?'':FtStore.canWrite?(f.example?`<button class="btn" data-ftdup="${esc(f.id)}">Duplicate and edit</button>`:`<button class="btn" data-ftedit="${esc(f.id)}">Edit</button>`):''}</div></div>
    ${f.description||f.summary?`<p class="sc-desc">${esc(f.description||f.summary)}</p>`:''}</div>`;
}
function ftEpicHTML(ep){
  const r=FeatureImpact.epic(D,ep,ftAll()), fs=ftAll().filter(f=>f.epic===ep.id);
  return ftHead({id:ep.id,name:ep.name,summary:ep.summary,owner:ep.owner},r,true)
   +`<section class="panel" style="margin-bottom:12px"><h2>Features</h2><div class="tbl-wrap"><table><thead><tr><th>Feature</th><th>Status</th><th>Target</th><th>Impact</th><th class="num">Apps</th><th class="num">Issues</th></tr></thead><tbody>
     ${fs.map(f=>{const x=ftRun(f);return `<tr data-ftsel="${esc(f.id)}" style="cursor:pointer"><td><b style="font-weight:600">${esc(f.name)}</b> <span class="mono muted">${f.saved?'saved':esc(f.id)}</span></td><td>${pill(f.status,FT_ST_CLS[f.status])}</td><td class="mono">${esc(f.target)}</td><td>${pill(x.level,FT_LVL_CLS[x.level])}</td><td class="num mono">${x.direct.length}</td><td class="num mono">${x.flags.filter(y=>y.sev!=='info').length||''}</td></tr>`}).join('')}</tbody></table></div></section>`
   +ftImpactHTML({drivers:ep.drivers,depends:[],new_ifs:fs.flatMap(f=>f.new_ifs||[])},r);
}
function change(){
  const tab=state.ftTab||'backlog';
  const all=ftAll(), rs=all.map(f=>({f,r:ftRun(f)}));
  const byLv=l=>rs.filter(x=>x.r.level===l).length, block=rs.filter(x=>x.r.flags.some(y=>y.sev==='crit')).length;
  $('#view').innerHTML=`<div class="filters" style="justify-content:space-between">
     <div class="seg" role="tablist">${[['backlog','Backlog and impact'],['roadmap','Roadmap and hotspots'],['portfolio','Portfolio table']].map(([k,l])=>`<button data-fttab="${k}" aria-pressed="${tab===k}">${l}</button>`).join('')}</div>
     ${FtStore.canWrite?'<button class="btn" data-ftnew="1">Model a new feature</button>':''}</div>
   <p class="sub muted" style="margin:-4px 0 12px;font-size:12.5px">${all.length} features in ${D.epics.length} epics. ${byLv('Critical')} critical and ${byLv('High')} high change impact; ${block} with a blocker. Pick what a feature changes and the atlas traces the effect on integrations, journeys, people, data, suppliers, resilience, regulation${PG?', '+esc(PNAME):''} and other work in flight. ${FtStore.mode==='shared'?'Features you model are shared with everyone who can open this dashboard.':'Features you model are saved in this browser.'} The example backlog is illustrative.</p>
   <div id="ft-msg">${FtStore.msg?`<div class="callout" style="margin-bottom:12px">${esc(FtStore.msg)}</div>`:''}</div>
   <div id="ft-body"></div>`;
  if(tab==='roadmap') return ftRoadmap(rs);
  if(tab==='portfolio') return ftPortfolio(rs);
  ftBacklog();
}
function ftRefresh(){if(state.view!=='change')return; if(ftDraft&&document.getElementById('ft-main')){ftListRender();return} change()}
function ftBacklog(){
  $('#ft-body').innerHTML=`<div class="sc-wrap"><nav class="sc-list" id="ft-list" aria-label="Epics and features"></nav><div class="sc-main" id="ft-main"></div></div>`;
  ftListRender();
  if(ftDraft) return ftEditor();
  const sel=state.ftSel||FIRST.feat;
  if(EP[sel]) $('#ft-main').innerHTML=ftEpicHTML(EP[sel]); else { const f=ftFind(sel)||ftAll()[0]; if(!f){$('#ft-main').innerHTML='<p class="empty">No features yet. Model a new feature to start.</p>';return} state.ftSel=f.id; $('#ft-main').innerHTML=ftHead(f,ftRun(f))+ftImpactHTML(f,ftRun(f)); }
}
function ftListRender(){
  const el=document.getElementById('ft-list'); if(!el) return;
  const all=ftAll();
  const item=f=>{const r=ftRun(f);return `<button class="sc-item ${state.ftSel===f.id&&!ftDraft?'on':''}" data-ftsel="${esc(f.id)}"><span class="sc-item-t">${esc(f.name)}</span><span class="sc-item-m">${pill(r.level,FT_LVL_CLS[r.level])}<span class="mono">${esc(f.target)}</span>${esc(f.status)}</span></button>`};
  const saved=all.filter(f=>f.saved), isNew=ftDraft&&!FtStore.items.some(x=>x.id===ftDraft.id);
  el.innerHTML=(isNew?`<h4>Editing</h4><button class="sc-item on draft" data-ftfocus="1"><span class="sc-item-t">${esc(ftDraft.name||'New feature')}</span><span class="sc-item-m">Not saved yet</span></button>`:'')+(saved.length?`<h4>Modelled <code>${saved.length}</code></h4>${saved.map(item).join('')}`:'')
   +D.epics.map(ep=>`<h4 style="margin-top:10px"><button class="linklike" data-ftsel="${ep.id}" style="text-transform:uppercase;letter-spacing:.09em;font:inherit;color:inherit">${esc(ep.name)}</button><code>${ep.id}</code></h4>${all.filter(f=>f.example&&f.epic===ep.id).map(item).join('')}`).join('');
}
function ftRoadmap(rs){
  const qs=[...new Set(rs.map(x=>x.f.target).filter(Boolean))].sort((a,b)=>FeatureImpact.q2n(a)-FeatureImpact.q2n(b));
  const cell=(ep,q)=>rs.filter(x=>x.f.epic===ep&&x.f.target===q).map(x=>`<button class="ft-pill lv-${x.r.level.toLowerCase()}" data-ftgo="${esc(x.f.id)}" title="${esc(x.f.name)} · ${x.r.level} impact · ${esc(x.f.status)}">${esc(x.f.saved?'New':x.f.id)}${x.r.flags.some(y=>y.sev==='crit')?' !':''}</button>`).join('');
  const appCnt={}; rs.forEach(x=>{if(x.f.status==='Done')return; Object.entries(x.f.apps).forEach(([a,c])=>{if(c==='Configure')return;(appCnt[a]=appCnt[a]||{});appCnt[a][x.f.target]=(appCnt[a][x.f.target]||0)+1})});
  const top=Object.keys(appCnt).sort((a,b)=>Object.values(appCnt[b]).reduce((s,v)=>s+v,0)-Object.values(appCnt[a]).reduce((s,v)=>s+v,0)).slice(0,16);
  $('#ft-body').innerHTML=`<section class="panel" style="margin-bottom:12px"><h2>Roadmap by epic</h2><p class="sub">Each box is a feature, coloured by change impact. ! marks a blocker. Click a feature for its impact.</p>
    <div class="tbl-wrap"><table class="ft-road"><thead><tr><th>Epic</th>${qs.map(q=>`<th>${q}</th>`).join('')}</tr></thead><tbody>
    ${[...D.epics.map(e=>e.id),...(rs.some(x=>!EP[x.f.epic])?['']:[])].map(ep=>`<tr><td><button class="linklike" data-ftgo="${ep}">${esc(EP[ep]?EP[ep].name:'No epic')}</button></td>${qs.map(q=>`<td>${cell(ep,q)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
    <div class="legend">${['Low','Medium','High','Critical'].map(l=>`<span><i class="ft-dot d-${l.toLowerCase()}"></i>${l}</span>`).join('')}</div></section>
   <section class="panel"><h2>Change hotspots</h2><p class="sub">Features that change each application, by target quarter (configuration-only changes and completed features left out). Three or more in one quarter means release and test contention.</p>
    <div class="tbl-wrap"><table class="ft-heat"><thead><tr><th>Application</th>${qs.map(q=>`<th>${q}</th>`).join('')}<th class="num">Total</th></tr></thead><tbody>
    ${top.map(a=>{const t=Object.values(appCnt[a]).reduce((s,v)=>s+v,0);return `<tr data-ent="app:${a}"><td>${esc(AP[a].name)} <span class="muted mono">${AP[a].tier}</span></td>${qs.map(q=>{const n=appCnt[a][q]||0;return `<td class="num mono" style="${n?`background:color-mix(in oklab,var(--${n>=3?'crit':n===2?'warn':'accent'}) ${n>=3?30:n===2?24:12}%,var(--surface))`:''}">${n||''}</td>`}).join('')}<td class="num mono"><b>${t}</b></td></tr>`}).join('')}</tbody></table></div></section>`;
}
function ftPortfolio(rs){
  const order={Critical:0,High:1,Medium:2,Low:3};
  $('#ft-body').innerHTML=`<section class="panel"><h2>All features by change impact</h2><div class="tbl-wrap"><table><thead><tr><th>Feature</th><th>Epic</th><th>Status</th><th>Target</th><th>Impact</th><th class="num">Apps</th><th class="num">Partners</th><th class="num">Journeys</th><th class="num">Retrain</th><th class="num">Blockers</th><th class="num">Checks</th></tr></thead><tbody>
   ${rs.sort((a,b)=>order[a.r.level]-order[b.r.level]||b.r.score-a.r.score).map(x=>`<tr data-ftgo="${esc(x.f.id)}" style="cursor:pointer"><td><b style="font-weight:600">${esc(x.f.name)}</b> <span class="mono muted">${x.f.saved?'modelled':esc(x.f.id)}</span></td><td style="font-size:12.5px">${esc(EP[x.f.epic]?EP[x.f.epic].name:'')}</td><td>${pill(x.f.status,FT_ST_CLS[x.f.status])}</td><td class="mono">${esc(x.f.target)}</td><td>${pill(x.r.level,FT_LVL_CLS[x.r.level])}</td><td class="num mono">${x.r.direct.length}</td><td class="num mono">${x.r.partners.length}</td><td class="num mono">${x.r.journeys.length}</td><td class="num mono">${x.r.retrain.length}</td><td class="num mono">${x.r.flags.filter(y=>y.sev==='crit').length||''}</td><td class="num mono">${x.r.flags.filter(y=>y.sev==='warn').length||''}</td></tr>`).join('')}</tbody></table></div></section>`;
}
// ---------- editor
function ftBlank(){const y=TODAY.getFullYear(),q=Math.floor(TODAY.getMonth()/3)+1,t=q>=3?`${y+1}-Q${q-2}`:`${y}-Q${q+2}`;return {id:ftNewId(),name:'',epic:'',status:'Idea',target:t,size:'M',owner:(D.roles.find(r=>/product owner/i.test(r.name))||D.roles.find(r=>r.family==='Technology')||D.roles[0]).id,description:'',apps:{},caps:[],steps:[],new_ifs:[],drivers:[],depends:[]}}
function ftOpenEditor(f){ftDraft=JSON.parse(JSON.stringify(f)); delete ftDraft.saved; delete ftDraft.example; ftDelArm=null; state.ftTab='backlog'; if(!document.getElementById('ft-main')) return change(); ftEditor(); ftListRender()}
function ftOpts(list,sel){return list.map(([v,l])=>`<option value="${esc(v)}" ${v===sel?'selected':''}>${esc(l)}</option>`).join('')}
function ftPickers(){
  const d=ftDraft;
  const appRows=Object.entries(d.apps).map(([a,c])=>`<div class="ft-row"><span>${esc(AP[a].name)}</span><select data-ftch="${a}">${ftOpts(FeatureImpact.CHANGE_TYPES.map(x=>[x,x]),c)}</select><button class="btn ghost" data-ftrm="apps:${a}" aria-label="Remove">Remove</button></div>`).join('');
  const chips=(k,label)=>d[k].length?`<div class="chips">${d[k].map(x=>`<button class="chip" data-ftrm="${k}:${x}"><code>${esc(x)}</code>${esc(label(x))} ✕</button>`).join('')}</div>`:'';
  const appsSorted=D.apps.slice().sort((a,b)=>a.name.localeCompare(b.name));
  return `<div class="sc-f" id="ft-f-apps"><span>Applications and what changes</span>${appRows||'<p class="empty" style="text-transform:none;letter-spacing:0">Add at least one application.</p>'}
     <div class="ft-row"><select id="ft-addapps"><option value="">Choose an application</option>${appsSorted.filter(a=>!d.apps[a.id]).map(a=>`<option value="${a.id}">${esc(a.name)} (${a.id})</option>`).join('')}</select><select id="ft-addch">${ftOpts(FeatureImpact.CHANGE_TYPES.map(x=>[x,x]),'Enhance')}</select><button class="btn" data-ftadd="apps">Add</button></div></div>
   <div class="sc-f"><span>L3 capabilities created or changed</span>${chips('caps',x=>CAP[x].name)}
     <div class="ft-row"><select id="ft-addcaps"><option value="">Choose a capability</option>${L2.map(c=>`<optgroup label="${esc(c.name)}">${(L3of[c.id]||[]).filter(x=>!d.caps.includes(x.id)).map(x=>`<option value="${x.id}">${esc(x.name)}</option>`).join('')}</optgroup>`).join('')}</select><button class="btn" data-ftadd="caps">Add</button></div></div>
   <div class="sc-f"><span>Journey steps whose way of working changes</span>${chips('steps',x=>ST[x].name)}
     <div class="ft-row"><select id="ft-addsteps"><option value="">Choose a step</option>${D.value_streams.map(v=>`<optgroup label="${esc(v.name)}">${D.steps.filter(s=>s.vs===v.id&&!d.steps.includes(s.id)).map(s=>`<option value="${s.id}">${esc(s.name)}</option>`).join('')}</optgroup>`).join('')}</select><button class="btn" data-ftadd="steps">Add</button></div></div>
   <div class="sc-f"><span>Serves (initiative, requirement${PG?' or '+esc(PDEC.toLowerCase()):''})</span>${chips('drivers',ftDriverName)}
     <div class="ft-row"><select id="ft-adddrivers"><option value="">Choose a driver</option><optgroup label="Strategic initiatives">${D.strategy.initiatives.map(i=>`<option value="${i.id}">${esc(i.title)}</option>`).join('')}</optgroup><optgroup label="Regulatory requirements">${D.regulations.flatMap(r=>r.requirements).map(q=>`<option value="${q.id}">${q.id} ${esc(q.short)}</option>`).join('')}</optgroup>${PG?`<optgroup label="${esc(PDEC)}s">${(PG.decisions||[]).map(b=>`<option value="${b.id}">${b.id} ${esc(b.title)}</option>`).join('')}</optgroup>`:''}</select><button class="btn" data-ftadd="drivers">Add</button></div></div>
   <div class="sc-f"><span>Depends on</span>${chips('depends',x=>(ftFind(x)||{}).name||x)}
     <div class="ft-row"><select id="ft-adddepends"><option value="">Choose a feature</option>${ftAll().filter(f=>f.id!==d.id&&!d.depends.includes(f.id)).map(f=>`<option value="${esc(f.id)}">${esc(f.saved?'':f.id+' ')}${esc(f.name)}</option>`).join('')}</select><button class="btn" data-ftadd="depends">Add</button></div></div>`;
}
function ftEditor(){
  const d=ftDraft, isSaved=FtStore.items.some(x=>x.id===d.id);
  $('#ft-main').innerHTML=`<div class="ed-head" id="ft-edhead" tabindex="-1"><div><div class="k">Change impact</div><h2 class="sc-title" style="margin:2px 0 4px">${isSaved?'Edit feature':'Model a new feature'}</h2>
     <p class="sub" style="margin:0">${isSaved?'Change the details and save.':'Name it, then add what it changes. The impact preview below updates as you go. Nothing is saved until you press Save feature.'}</p></div>
     <button class="btn ghost" data-ftcancel="1">Back to backlog</button></div><div class="sc-head" style="margin:0">${d.seededFrom?`<div class="callout" style="margin-top:8px">Started from ${esc(d.seededFrom)}. Set the change type for each application, remove what does not change, and add steps, capabilities and drivers. The preview below updates as you go.</div>`:''}</div>
   <div class="sc-form panel" style="margin-bottom:12px">
    <div class="ft-two"><label class="sc-f" id="ft-f-name"><span>Name</span><input id="ft-name" value="${esc(d.name)}" placeholder="For example: Online address change"></label>
     <label class="sc-f"><span>Epic</span><select id="ft-epic"><option value="">No epic</option>${ftOpts(D.epics.map(e=>[e.id,e.name]),d.epic)}</select></label></div>
    <div class="ft-four"><label class="sc-f"><span>Status</span><select id="ft-status">${ftOpts(FeatureImpact.STATUS.map(x=>[x,x]),d.status)}</select></label>
     <label class="sc-f"><span>Target quarter</span><select id="ft-target">${ftOpts(FT_Q.map(x=>[x,x]),d.target)}</select></label>
     <label class="sc-f"><span>Size</span><select id="ft-size">${ftOpts(['S','M','L','XL'].map(x=>[x,x]),d.size)}</select></label>
     <label class="sc-f"><span>Owner</span><select id="ft-owner">${ftOpts(D.roles.map(r=>[r.id,r.name]),d.owner)}</select></label></div>
    <label class="sc-f"><span>Description</span><textarea id="ft-desc" rows="2">${esc(d.description)}</textarea></label>
    <div id="ft-pickers">${ftPickers()}</div>
    <div id="ft-ready" class="ed-ready" aria-live="polite"></div>
    <p id="ft-formmsg" class="ed-alert" role="alert" hidden></p>
    <div class="sc-actions"><button class="btn" data-ftsave="1" aria-describedby="ft-ready">Save feature</button><button class="btn ghost" data-ftcancel="1">Cancel</button>${isSaved?`<button class="btn ghost" data-ftdel="${esc(d.id)}">Delete</button>`:''}</div>
   </div>
   <h3 class="gd-h" style="margin-top:6px">Impact preview</h3><div id="ft-preview"></div>`;
  ftPreview();
  edFocus(document.getElementById('ft-main'),'ft-name');
}
function ftReadForm(){const v=id=>(document.getElementById(id)||{}).value; if(!ftDraft) return;
  ftDraft.name=v('ft-name')??ftDraft.name; ftDraft.epic=v('ft-epic')??ftDraft.epic; ftDraft.status=v('ft-status')||ftDraft.status; ftDraft.target=v('ft-target')||ftDraft.target;
  ftDraft.size=v('ft-size')||ftDraft.size; ftDraft.owner=v('ft-owner')||ftDraft.owner; ftDraft.description=v('ft-desc')??ftDraft.description;
  document.querySelectorAll('[data-ftch]').forEach(s=>{ftDraft.apps[s.dataset.ftch]=s.value});}
function ftReadyItems(d){return [{f:'name',label:'Give the feature a name',ok:!!String(d.name||'').trim()},{f:'apps',label:'Add at least one application under "Applications and what changes"',ok:Object.keys(d.apps||{}).length>0}]}
function ftReadyRender(){edReady('ft',ftDraft?ftReadyItems(ftDraft):[],'feature')}
function ftPreview(){ftReadyRender();const p=document.getElementById('ft-preview'); if(!p) return;
  if(!Object.keys(ftDraft.apps).length){p.innerHTML='<p class="empty">Add an application to see the impact.</p>';return}
  p.innerHTML=ftImpactHTML(ftDraft,ftRun(ftDraft));}
function ftDrawer(type,id){
  let html='';
  if(type==='epic'){const ep=EP[id], r=FeatureImpact.epic(D,ep,ftAll());
    html=`<header><div class="t"><div class="k">Epic · ${id}</div><h2>${esc(ep.name)}</h2><div class="chips">${pill('Change impact: '+r.level,FT_LVL_CLS[r.level])}<span class="pill s-neutral">${r.features.length} features</span>${conf('Illustrative')}</div></div><button class="x" id="dclose" aria-label="Close">✕</button></header>
     <div class="body"><p style="margin:0;font-size:14px;line-height:1.6">${esc(ep.summary)}</p>${dl([['Owner',chip('role',ep.owner,RO[ep.owner].name,false)],['Serves',ep.drivers.map(ftDriverChip).join(' ')],['Window',esc((r.first||'')+' to '+(r.last||''))]])}
     ${sec('Features',`<div class="chips">${r.features.map(f=>chip('feat',f,ftFind(f).name)).join('')}</div>`)}
     ${sec('Applications changed',appChips(r.direct.map(x=>x.app)))}
     ${sec('Issues',ftFlagsHTML(r.flags.slice(0,8)))}
     <div><button class="btn" data-ftgo="${id}">Open in Change impact</button></div></div>`;}
  else {const f=ftFind(id), r=ftRun(f);
    html=`<header><div class="t"><div class="k">Feature · ${f.saved?'modelled':id}${EP[f.epic]?' · '+esc(EP[f.epic].name):''}</div><h2>${esc(f.name)}</h2><div class="chips">${pill(f.status,FT_ST_CLS[f.status])}<span class="pill s-neutral">${esc(f.target)}</span>${pill('Change impact: '+r.level,FT_LVL_CLS[r.level])}${f.example?conf('Illustrative'):''}</div></div><button class="x" id="dclose" aria-label="Close">✕</button></header>
     <div class="body">${f.description?`<p style="margin:0;font-size:14px;line-height:1.6">${esc(f.description)}</p>`:''}
     ${sec('Applications changed',`<div class="chips">${r.direct.map(x=>`<button class="chip" data-ent="app:${x.app}"><code>${x.change}</code>${esc(AP[x.app].name)}</button>`).join('')}</div>`)}
     ${dl([['Owner',f.owner&&RO[f.owner]?chip('role',f.owner,RO[f.owner].name,false):''],['Serves',(f.drivers||[]).map(ftDriverChip).join(' ')],['Footprint',`${r.partners.length} integration partners · ${r.journeys.length} journeys · ${r.retrain.length} roles to retrain · ${r.procs.length} processes`]])}
     ${sec('Issues',ftFlagsHTML(r.flags))}
     <div><button class="btn" data-ftgo="${esc(id)}">Open full impact</button></div></div>`;}
  $('#drawer').innerHTML=html; $('#drawer').hidden=false;$('#scrim').hidden=false;$('#drawer').querySelector('.body').scrollTop=0;$('#dclose').focus();
}
function ftFeaturesFor(pred){return ftAll().filter(pred).map(f=>{const r=ftRun(f);return `<tr data-ent="feat:${esc(f.id)}"><td>${esc(f.name)}<div class="muted" style="font-size:12px">${esc(f.target)} · ${esc(f.status)}</div></td><td>${pill(r.level,FT_LVL_CLS[r.level])}</td></tr>`}).join('')}
// ---------- Model impact from any element
const FT_MODEL_TYPES=['app','sup','cap','step','vs','bp','si'];
function ftCanModel(type,id){ // kept for compatibility
  if(!FtStore.canWrite||FT_MODEL_TYPES.indexOf(type)<0) return false;
  const s=ftSeed(type,id); return !!s&&(Object.keys(s.apps).length>0||s.steps.length>0);
}
function ftSeed(type,id){
  const f=ftBlank(), add=(a,c)=>{if(AP[a]&&!f.apps[a]) f.apps[a]=c||'Enhance'};
  if(type==='app'){if(!AP[id])return null; add(id); f.name='Change to '+AP[id].name; f.owner=AP[id].tech_owner||f.owner; f.seededFrom='application '+AP[id].name}
  else if(type==='sup'){if(!SU[id])return null; D.apps.filter(a=>a.vendor===id).forEach(a=>add(a.id)); f.name='Change with '+SU[id].name; f.seededFrom='supplier '+SU[id].name+' (its products)'}
  else if(type==='cap'){const c=CAP[id]; if(!c)return null;
    if(c.level===3){f.caps=[id]; c.apps.forEach(a=>add(a)); f.seededFrom='L3 capability '+c.name}
    else {(capApps[id]||[]).forEach(a=>add(a)); f.seededFrom='capability '+c.name+' (its applications)'}
    f.name='Change to '+c.name}
  else if(type==='step'){const t=ST[id]; if(!t)return null; f.steps=[id]; t.apps.forEach(a=>add(a)); f.name='Change to '+t.name; f.seededFrom='journey step '+t.name}
  else if(type==='vs'){const v=VS[id]; if(!v)return null; const ss=D.steps.filter(x=>x.vs===id); f.steps=ss.map(x=>x.id); ss.forEach(x=>x.apps.forEach(a=>add(a,'Configure'))); f.name='Change to '+v.name; f.seededFrom='journey '+v.name+' (all steps; applications set to Configure)'}
  else if(type==='bp'){const b=BP[id]; if(!b)return null; const kids=D.business_processes.filter(x=>x.parent===id); (b.level===1?[...new Set(kids.flatMap(x=>x.apps))]:b.apps).forEach(a=>add(a)); f.name='Change to '+b.name; f.owner=b.owner; f.seededFrom='process '+b.name+' (its applications)'}
  else if(type==='si'){const i=SI[id]; if(!i)return null; f.drivers=[id]; i.apps.forEach(a=>add(a)); f.name='Deliver '+i.title; f.seededFrom='strategic initiative '+i.title}
  else return null;
  return f;
}
// What if menu: a change (Change impact) or an event (What if? view), depending on the item
function wiOptions(type,id){
  const o=[], seed=ftSeed(type,id), apps=seed?Object.keys(seed.apps):[];
  if(seed&&FtStore.canWrite&&(apps.length||seed.steps.length)) o.push({k:'change',tag:'Change',t:'We change it',d:'Plan a feature: see integrations to retest or rework, journeys, people to retrain, programme and regulatory checks. Opens in Change impact'});
  const canSc=typeof ScStore!=='undefined'&&ScStore.canWrite;
  if(!canSc) return o;
  if(type==='app'){
    const plat=!!AP[id].platform;
    o.push({k:plat?'platform_failure':'app_outage',tag:'Event',t:'It becomes unavailable',d:`Outage: what goes down or degrades, ${CR.plural}, recovery time and DR issues. Opens in What if?`});
    o.push({k:'decommission',tag:'Decision',t:'We retire or replace it',d:'What must be re-hosted, re-integrated and migrated, and the run cost released. Opens in What if?'});
  }
  if(type==='sup'){
    o.push({k:'supplier_failure',tag:'Event',t:'The supplier fails or exits',d:'Every application it provides, hosts or supports, and what that takes down. Opens in What if?'});
    o.push({k:'price_change',tag:'Event',t:'The supplier changes its prices',d:'Cost effect on licences and support, starting at plus 10 per cent. Opens in What if?'});
  }
  if((type==='cap'||type==='step'||type==='bp')&&apps.length&&apps.length<=8) o.push({k:'app_outage',tag:'Event',t:'Its applications become unavailable',d:apps.length+' application'+(apps.length>1?'s':'')+' out at once: knock-on effect and recovery. Opens in What if?'});
  return o;
}
function wiGo(kind,type,id){
  closeDrawer();
  if(kind==='change'){const f=ftSeed(type,id); if(!f) return; ftDraft=f; state.ftTab='backlog'; save(); if(state.view!=='change') go('change'); else change();
    const nm=document.getElementById('ft-name'); if(nm){nm.focus(); nm.select&&nm.select()} return}
  const seed=ftSeed(type,id), sc=scBlank(); sc.type=kind;
  const nm=type==='app'?AP[id].name:type==='sup'?SU[id].name:(seed?seed.name.replace(/^Change to /,''):id);
  if(kind==='supplier_failure'||kind==='price_change'){sc.targets=[id]; sc.name=(kind==='price_change'?'Price rise from ':'Loss of ')+nm; sc.pct=10}
  else if(kind==='app_outage'||kind==='platform_failure'){sc.targets=type==='app'?[id]:Object.keys(seed.apps); sc.name=nm+' unavailable'}
  else if(kind==='decommission'){sc.targets=[id]; sc.name='Retire or replace '+nm}
  sc.description='Started from '+(seed&&seed.seededFrom?seed.seededFrom:nm)+'.';
  scDraft=sc; scDelArm=null; state.scTab='library'; save();
  if(state.view!=='scenarios') go('scenarios'); else scenarios();
  const n=document.getElementById('sc-name'); if(n){n.focus(); n.select&&n.select()}
}
document.addEventListener('click',e=>{
  const w=e.target.closest('[data-whatif]');
  if(w){e.stopPropagation(); const [type,id]=w.dataset.whatif.split(/:(.+)/); const box=w.closest('.drawer-actions').nextElementSibling;
    if(!box||!box.classList.contains('wi-menu')) return;
    if(!box.hidden){box.hidden=true; w.setAttribute('aria-expanded','false'); return}
    const opts=wiOptions(type,id);
    box.innerHTML=`<div class="k">What do you want to model?</div>${opts.map(o=>`<button class="wi-opt" data-wigo="${o.k}|${type}|${esc(id)}"><i>${o.tag}</i><b>${esc(o.t)}</b><span>${esc(o.d)}</span></button>`).join('')}`;
    box.hidden=false; w.setAttribute('aria-expanded','true'); const first=box.querySelector('.wi-opt'); if(first) first.focus(); return}
  const g=e.target.closest('[data-wigo]');
  if(g){e.stopPropagation(); const [kind,type,id]=g.dataset.wigo.split('|'); return wiGo(kind,type,id)}
},true);
document.addEventListener('click',e=>{
  const m=e.target.closest('[data-ftmodel]'); if(!m) return;
  e.stopPropagation(); const [type,id]=m.dataset.ftmodel.split(/:(.+)/); const f=ftSeed(type,id); if(!f) return;
  closeDrawer(); ftDraft=f; state.ftTab='backlog'; save();
  if(state.view!=='change') go('change'); else change();
  const nm=document.getElementById('ft-name'); if(nm){nm.focus(); nm.select&&nm.select()}
},true);
// ---------- events
document.addEventListener('click',async e=>{
  const g=e.target.closest('[data-ftgo]');
  if(g){e.stopPropagation(); closeDrawer(); ftDraft=null; state.ftSel=g.dataset.ftgo||state.ftSel; state.ftTab='backlog'; save(); if(state.view!=='change') return go('change'); return change()}
  const rq=e.target.closest('[data-ftreq]');
  if(rq){e.stopPropagation(); closeDrawer(); state.scTab='library'; const ex=D.example_scenarios.find(x=>x.type==='regulatory_change'); if(ex) state.scSel=ex.id; save(); return go('scenarios')}
  if(state.view!=='change') return;
  const t=e.target.closest('[data-ftfocus],[data-fttab],[data-ftnew],[data-ftsel],[data-ftdup],[data-ftedit],[data-ftadd],[data-ftrm],[data-ftsave],[data-ftcancel],[data-ftdel]');
  if(!t) return;
  e.stopPropagation();
  if(t.dataset.ftfocus){return edFocus(document.getElementById('ft-main'),'ft-name')}
  if(t.dataset.fttab){state.ftTab=t.dataset.fttab;ftDraft=null;save();return change()}
  if(t.dataset.ftnew) return ftOpenEditor(ftBlank());
  if(t.dataset.ftsel){ftDraft=null;state.ftSel=t.dataset.ftsel;save();if(!document.getElementById('ft-main'))return change();ftBacklog();window.scrollTo&&window.scrollTo(0,0);return}
  if(t.dataset.ftdup){const f=ftFind(t.dataset.ftdup);const c=JSON.parse(JSON.stringify(f));c.id=ftNewId();c.name=f.name+' (copy)';delete c.author;delete c.createdAt;delete c.updatedAt;return ftOpenEditor(c)}
  if(t.dataset.ftedit) return ftOpenEditor(ftFind(t.dataset.ftedit));
  if(t.dataset.ftadd){ftReadForm();const k=t.dataset.ftadd,v=(document.getElementById('ft-add'+k)||{}).value;if(!v)return;
    if(k==='apps') ftDraft.apps[v]=(document.getElementById('ft-addch')||{}).value||'Enhance'; else if(!ftDraft[k].includes(v)) ftDraft[k].push(v);
    document.getElementById('ft-pickers').innerHTML=ftPickers();return ftPreview()}
  if(t.dataset.ftrm){ftReadForm();const [k,v]=t.dataset.ftrm.split(/:(.+)/);if(k==='apps')delete ftDraft.apps[v];else ftDraft[k]=ftDraft[k].filter(x=>x!==v);document.getElementById('ft-pickers').innerHTML=ftPickers();return ftPreview()}
  if(t.dataset.ftcancel){ftDraft=null;return ftBacklog()}
  if(t.dataset.ftdel){if(ftDelArm!==t.dataset.ftdel){ftDelArm=t.dataset.ftdel;t.textContent='Confirm delete';return}
    const ok=await ftDelete(t.dataset.ftdel);if(ok){ftDraft=null;state.ftSel=FIRST.feat;save();change()}else ftRefresh();return}
  if(t.dataset.ftsave){ftReadForm();
    if(!edBlockSave('ft',ftReadyItems(ftDraft),'feature',{name:'ft-name',apps:'ft-addapps'})) return;
    t.disabled=true;t.textContent='Saving…';const f=JSON.parse(JSON.stringify(ftDraft));const ok=await ftSave(f);
    if(ok){ftDraft=null;state.ftSel=f.id;save();change()}else{t.disabled=false;t.textContent='Save feature';edAlert('ft',FtStore.msg)}return}
},true);
document.addEventListener('input',e=>{if(state.view!=='change'||!ftDraft||e.target.id!=='ft-name') return; ftDraft.name=e.target.value; const it=document.querySelector('#ft-list .draft .sc-item-t'); if(it) it.textContent=e.target.value||'New feature'; ftReadyRender()});
document.addEventListener('change',e=>{if(state.view!=='change'||!ftDraft) return; if(e.target.closest('.sc-form')&&!/^ft-add/.test(e.target.id)){ftReadForm();ftPreview()}});

// ---------- Regulatory readiness, derived from the change backlog (features that list a requirement as a driver)
const RD_RANK={'Done':1,'On track':2,'Late':3,'Not planned':4};
const RD_CLS={'Done':'ok','On track':'neutral','Late':'warn','Not planned':'crit'};
function rdRegs(){return (D.regulations||[]).filter(r=>r.readiness!==false&&r.requirements.length&&Object.values(r.dates||{}).some(isDate))}
function rdReg(){const rs=rdRegs(); return rs.find(r=>r.id===state.regSel)||rs[0]}
function rdPicker(){const rs=rdRegs(), cur=rdReg(); return `<label style="align-self:flex-end">Regulation <select data-regsel="1">${rs.map(r=>`<option value="${esc(r.id)}" ${r.id===cur.id?'selected':''}>${esc(r.short||r.name)}</option>`).join('')}</select></label>`}
function rdQs(reg){return (reg?[reg]:[]).flatMap(r=>r.requirements.map(q=>Object.assign({reg:r},q)))}
function rdDeadline(q){const d=q.reg.dates||{}; return d[q.deadline]||d[q.reg.main_date||'general']||Object.values(d).filter(isDate).sort().pop()||''}
function rdStatus(q){
  const fs=ftAll().filter(f=>(f.drivers||[]).includes(q.id)), dl=rdDeadline(q);
  if(!fs.length) return {status:'Not planned',fs,dl};
  if(fs.every(f=>f.status==='Done')) return {status:'Done',fs,dl};
  const last=fs.map(f=>f.target).filter(Boolean).sort((a,b)=>FeatureImpact.q2n(a)-FeatureImpact.q2n(b)).pop();
  const dq=dl?FeatureImpact.q2n(dl.slice(0,4)+'-Q'+(Math.floor((+dl.slice(5,7)-1)/3)+1)):null;
  return {status:dq!=null&&last&&FeatureImpact.q2n(last)>dq?'Late':'On track',fs,dl,last};
}
function rdSummary(){const o={total:0,'Done':0,'On track':0,'Late':0,'Not planned':0}; rdQs(rdReg()).forEach(q=>{o.total++;o[rdStatus(q).status]++}); return o}
function rdWorst(qs){let w=null; qs.forEach(q=>{const st=rdStatus(q).status; if(!w||RD_RANK[st]>RD_RANK[w]) w=st}); return w}
function rdCap(id){const qs=rdQs(rdReg()).filter(q=>q.caps.includes(id)); const w=rdWorst(qs); return {n:qs.length,rank:w?RD_RANK[w]:0,status:w||'Not in scope'}}
function rdApp(id){const qs=rdQs(rdReg()).filter(q=>q.apps.includes(id)); const w=rdWorst(qs); return {n:qs.length,status:w||'Not in scope'}}
function rdSec(pred){
  return rdRegs().map(reg=>{const qs=rdQs(reg).filter(pred); if(!qs.length) return '';
  return sec(`${esc(reg.short||reg.name)} requirements · ${qs.length}`,`<div class="tbl-wrap"><table><tbody>${qs.map(q=>{const r=rdStatus(q);
    return `<tr><td><span class="mono muted" style="font-size:11px">${q.id}</span> ${esc(q.short)}<div class="muted" style="font-size:12px">Deadline ${esc(r.dl||'to confirm')}${r.fs.length?' · '+r.fs.map(f=>`<button class="linklike" data-ent="feat:${esc(f.id)}">${esc(f.saved?'modelled':f.id)}</button> ${esc(f.target)}`).join(', '):''}</div></td><td style="text-align:right">${pill(r.status,RD_CLS[r.status])}</td></tr>`}).join('')}</tbody></table></div><p class="muted" style="font-size:12px;margin:6px 0 0">Readiness comes from the change backlog: a requirement is planned when a feature lists it as a driver.</p>`)}).join('');
}
document.addEventListener('change',e=>{if(!e.target.dataset||!e.target.dataset.regsel) return; state.regSel=e.target.value; save(); if(state.view==='landscape') landscape(); else if(state.view==='capabilities') capabilities()});
