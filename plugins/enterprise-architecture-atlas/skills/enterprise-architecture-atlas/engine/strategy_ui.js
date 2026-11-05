// ---------- Strategic priorities
const SG=D.strategy, SI=Object.fromEntries(SG.initiatives.map(i=>[i.id,i])), SPL=Object.fromEntries(SG.pillars.map(p=>[p.id,p]));
const siWeak=a=>['Migrate','Eliminate'].includes(AP[a].time)||AP[a].tech_health<3;
function siAlign(si){
  const weak=si.apps.filter(siWeak), crit=weak.filter(a=>AP[a].tier_n<=1);
  return {weak,crit,status:crit.length?'Watch':weak.length?'Minor gaps':'Aligned',cls:crit.length?'warn':weak.length?'neutral':'ok'};
}
const appInits=a=>SG.initiatives.filter(i=>i.apps.includes(a));
function strategy(){
  const used=[...new Set(SG.initiatives.flatMap(i=>i.apps))];
  const rows=used.map(a=>({a,inits:appInits(a)})).sort((x,y)=>y.inits.length-x.inits.length||AP[x.a].name.localeCompare(AP[y.a].name));
  const flagged=rows.filter(r=>siWeak(r.a));
  const caps=L2.filter(c=>c.strategic_initiatives>0).sort((a,b)=>b.strategic_initiatives-a.strategic_initiatives);
  const mx=caps.length?caps[0].strategic_initiatives:1;
  $('#view').innerHTML=`<section class="sg-theme"><span class="k">Strategic priorities</span><b>${esc(SG.theme)}</b>${SG.source?`<a href="${esc(SG.source)}" target="_blank" rel="noopener">${esc(SG.source_title||'Source')}</a>`:''}</section>
   <div class="sg-grid">${SG.pillars.map(p=>`<section class="sg-pillar ${p.kind==='Enabler'?'en':''}"><header><span class="k">${esc(p.kind)}</span><b>${esc(p.name)}</b>${p.cvs?`<button class="chip" data-cvs-go="${p.cvs}">Open ${esc(VSL.toLowerCase())}</button>`:''}</header>
     ${SG.initiatives.filter(i=>i.pillar===p.id).map(i=>{const al=siAlign(i);return `<button class="si-card" data-ent="si:${i.id}"><span class="si-t">${esc(i.title)}</span><span class="si-e">${esc(i.evidence)}</span>
       <span class="si-f"><span class="mono muted">${i.apps.length} apps · ${i.caps.length} capabilities</span>${pill(al.status,al.cls)}</span></button>`}).join('')}</section>`).join('')}</div>
   <div class="legend" style="margin:8px 0 18px"><span>${pill('Aligned','ok')} applications behind the initiative are rated Invest or healthy</span><span>${pill('Minor gaps','neutral')} some supporting applications are weak, none critical</span><span>${pill('Watch','warn')} a Tier 0 or Tier 1 application behind it is rated Migrate or Eliminate, or scores below 3 for technical health</span><span>Health scores are illustrative except where confirmed.</span></div>
   <div class="grid g-2" style="margin-bottom:16px">
    <section class="panel"><h2>Strategy depends on weak technology</h2><p class="sub">${flagged.length} of the ${used.length} applications behind the strategy are rated Migrate or Eliminate, or score below 3 for technical health. These are where the strategy and the portfolio disagree.</p>
      <div class="tbl-wrap"><table><thead><tr><th>Application</th><th>TIME</th><th class="num">Health</th><th>Initiatives</th>${PG?`<th>${esc(PLABEL)}</th>`:''}</tr></thead><tbody>
      ${flagged.map(r=>`<tr data-ent="app:${r.a}"><td><b style="font-weight:600">${esc(AP[r.a].name)}</b>${AP[r.a].crit?CRB():''}<div class="muted" style="font-size:12px">${esc(AP[r.a].product)}</div></td><td>${time(AP[r.a].time)}</td><td class="num mono">${AP[r.a].tech_health}</td><td style="font-size:12px">${r.inits.map(i=>esc(i.title)).join('; ')}</td>${PG?`<td style="font-size:12px">${esc(lensKey(AP[r.a].programme_lens))}</td>`:''}</tr>`).join('')||'<tr><td colspan="5" class="empty">None.</td></tr>'}
      </tbody></table></div></section>
    <section class="panel"><h2>Capabilities the strategy relies on</h2><p class="sub">Number of initiatives that depend on each capability. <button class="chip" data-nav="capabilities|caplens=strategy">See on the capability map</button></p>
      <div class="hbars">${caps.slice(0,16).map(c=>`<button class="hbar" data-ent="cap:${c.id}"><span class="nm">${esc(c.name)}</span><span class="trk"><span class="fil" style="display:block;width:${c.strategic_initiatives/mx*100}%"></span></span><span class="v">${c.strategic_initiatives}</span></button>`).join('')}</div></section>
   </div>
   <section class="panel"><h2>Applications carrying the strategy</h2><p class="sub">Every application behind at least one initiative, by number of initiatives.</p>
    <div class="tbl-wrap"><table><thead><tr><th>Application</th><th class="num">Initiatives</th><th>Pillars</th><th>TIME</th><th class="num">Health</th><th>Confidence</th></tr></thead><tbody>
    ${rows.map(r=>`<tr data-ent="app:${r.a}"><td><b style="font-weight:600">${esc(AP[r.a].name)}</b><div class="muted" style="font-size:12px">${esc(AP[r.a].product)}</div></td><td class="num mono">${r.inits.length}</td><td style="font-size:12px">${[...new Set(r.inits.map(i=>SPL[i.pillar].name))].map(esc).join(', ')}</td><td>${time(AP[r.a].time)}</td><td class="num mono">${AP[r.a].tech_health}</td><td>${conf(AP[r.a].confidence)}</td></tr>`).join('')}
    </tbody></table></div></section>`;
}
function openInitiative(id){
  const i=SI[id], p=SPL[i.pillar], al=siAlign(i);
  const sups=[...new Set(i.apps.flatMap(a=>appSups[a].map(x=>x.supplier)))];
  const roles=[...new Set(i.journeys.flatMap(v=>D.steps.filter(s=>s.vs===v).flatMap(s=>[...s.R,s.A])))];
  $('#drawer').innerHTML=`<header><div class="t"><div class="k">Strategic initiative · ${esc(p.name)}</div><h2>${esc(i.title)}</h2><div class="chips">${pill(al.status,al.cls)}<span class="pill s-neutral">${esc(p.kind)}</span>${conf(i.confidence||(SG.source?'Public':'Illustrative'))}</div></div><button class="x" id="dclose" aria-label="Close">✕</button></header>
   <div class="body"><p style="margin:0;font-size:14px;line-height:1.6">${esc(i.evidence)}</p>
   <p class="muted" style="font-size:12px;margin:0">Source: ${SG.source?`<a href="${esc(SG.source)}" target="_blank" rel="noopener">${esc(SG.source_title||'Source')}</a>`:esc(SG.source_title||'EA analysis')}. Mapping to the estate is EA analysis.</p>
   ${al.weak.length?`<div class="callout"><b>Alignment.</b> ${al.weak.map(a=>`${esc(AP[a].name)} (${AP[a].time}, health ${AP[a].tech_health})`).join('; ')} ${al.weak.length===1?'supports':'support'} this initiative but ${al.weak.length===1?'is':'are'} not rated to grow with it.</div>`:''}
   ${p.cvs?sec(VSL,`<div class="chips">${chip('cvs',p.cvs,CVS[p.cvs].name,false)}</div>`):''}
   ${i.journeys.length?sec('Journeys and process maps',`<div class="chips">${i.journeys.map(v=>`<button class="chip" data-pmap="${v}"><code>${v}</code>${esc(VS[v].name)} · map</button>`).join('')}</div>`):''}
   ${sec('Processes',`<div class="chips">${i.procs.map(b=>chip('bp',b,BP[b].name)).join('')}</div>`)}
   ${sec('Capabilities',`<div class="chips">${i.caps.map(c=>chip('cap',c,CAP[c].name)).join('')}</div>`)}
   ${sec(`Applications · ${i.apps.length}`,`<div class="tbl-wrap"><table><tbody>${i.apps.map(a=>`<tr data-ent="app:${a}"><td>${esc(AP[a].name)}<div class="muted" style="font-size:12px">${esc(AP[a].product)}</div></td><td>${time(AP[a].time)}</td><td class="mono" style="font-size:12px">health ${AP[a].tech_health}</td><td>${conf(AP[a].confidence)}</td></tr>`).join('')}</tbody></table></div>`)}
   ${roles.length?sec('Roles (responsible or accountable)',`<div class="chips">${roles.map(r=>chip('role',r,RO[r].name,false)).join('')}</div>`):''}
   ${sec('Suppliers',`<div class="chips">${sups.map(x=>chip('sup',x,SU[x].name,false)).join('')}</div>`)}
   ${(()=>{const rows=ftFeaturesFor(f=>(f.drivers||[]).includes(id)||(EP[f.epic]&&EP[f.epic].drivers.includes(id)));return rows?sec('Change features',`<div class="tbl-wrap"><table><tbody>${rows}</tbody></table></div>`):''})()}
   <div class="drawer-actions"><button class="btn ghost" data-trace-go="si:${i.id}">Trace connections</button><button class="btn ghost" data-whatif="si:${i.id}" aria-expanded="false" title="Model a change starting from this initiative">Model what if</button></div><div class="wi-menu" hidden></div></div>`;
  $('#drawer').hidden=false;$('#scrim').hidden=false;$('#drawer').querySelector('.body').scrollTop=0;$('#dclose').focus();
}
