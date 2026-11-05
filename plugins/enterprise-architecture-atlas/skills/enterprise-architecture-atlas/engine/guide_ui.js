// ---------- How to update (guide)
const AST=D.meta.assistant||'your assistant', CHAT=D.meta.host==='chat', REPO=D.meta.host==='repo', PFX=D.meta.file_prefix||'Atlas';
const GUIDE_ROUTES=CHAT?[
 {t:'Attach files in the chat',d:`Attach the documents to your message to ${AST}. Any format works: spreadsheets, PDFs, Visio or BPMN exports, slides, an Archi model, emails saved as files.`,w:'Attach to the chat'},
 {t:'Bring your atlas file',d:`Attach ${PFX}_atlas_model.json every time. It holds the whole atlas and its history; ${AST} cannot keep it between sessions.`,w:`${PFX}_atlas_model.json`},
 {t:'Send a link or a message',d:`Tell ${AST} what has changed, or paste a link. A short sentence is enough for a single fact.`,w:'Message'},
]:[
 {t:'Drop a file',d:'Put the document in the matching inbox folder of the atlas workspace. Any format works: spreadsheets, PDFs, Visio or BPMN exports, slides, an Archi model, emails saved as files.',w:'ea-atlas/inbox/<type>/'},
 {t:'Import an Archi model',d:'Put a .archimate file or an Open Group exchange file in inbox/archimate. Items keep their ArchiMate IDs, so a later import updates rather than duplicates.',w:'ea-atlas/inbox/archimate/'},
 {t:'Send a link or a message',d:`Add a link to sources/links.md, or tell ${AST} directly what has changed. A short sentence is enough for a single fact.`,w:'ea-atlas/sources/links.md'},
];
const GUIDE_FLOW=[
 ['Provide','New information goes in through one of the three routes above.'],
 ['Refresh',CHAT?`Ask ${AST} to refresh the atlas, with your atlas file and the new information attached.`:`Ask ${AST} to refresh the atlas. The enterprise-architecture-atlas skill reads the inbox and any links.`],
 ['Review',`${AST} lists what will be added, changed and retired, with any conflicts and questions. More than 10 changes, or any deletion, waits for your approval.`],
 ['Release','The version goes up, the change is recorded, and the Excel and dashboard are rebuilt and checked.'],
 ['Share',CHAT?`You get a new dashboard, Excel and atlas file. Replace the old copies wherever you keep them, for example SharePoint, and keep the new atlas file for next time.`:(REPO?'Commit the release. Open the new dashboard from output/, or publish output/ to an internal site so everyone sees the same version.':'The online dashboard is republished at the same link. Replace any intranet copy of the standalone file.')],
];
// type, inbox folder, intake tab (unused), what changes, suggested owner (role name pattern), view to check
const roleLike=re=>{const r=new RegExp(re,'i'); const m=D.roles.filter(x=>r.test(x.name)); return (m.find(x=>x.family==='Leadership')||m[0]||{}).id};
const GUIDE_TYPES=[
 ['Applications','applications','Applications','New or retired applications, product and version, TIME rating, criticality, hosting, runs on, data centre, business and technology owner','application services|enterprise architect|IT manager','apps'],
 ['Procurement and contracts','procurement','Procurement, Suppliers',`Supplier details, contract term, notice, auto-renew, change of control, ${TPR.terms_label}, annual value, exit plans`,'third-party|procurement|vendor','licensing'],
 ['Licences','licences','Licences','Entitlement, consumption, utilisation, compliance status, licence and support cost, renewal date','licence|software asset|procurement','licensing'],
 ['Roles','roles_raci','Roles','New, renamed or retired roles and their organisation unit','HR|people|human','roles'],
 ['RACI','roles_raci','RACI_Updates','Who is Responsible, Accountable, Consulted and Informed for each journey step. Each step keeps exactly one Accountable role','process|architect','roles'],
 ['Business process change','processes','Process_Updates','Step sequence, roles, applications and capabilities of an existing process or journey','process|architect','pmap'],
 ['New business process','processes','New_Processes','A new L2 process in Operate, Manage or Support. If it is customer facing end to end, a journey with steps and a process map is also created','process|architect','bpa'],
 ['Capabilities (L1 to L3)','capabilities','(message or file)','Capability names and descriptions, new L3 capabilities, application mapping, maturity ratings','enterprise architect|architect','capabilities'],
 ['Interfaces','interfaces','Interfaces',`Data flows between applications, integration type (${IFAMS.map(f=>f.name).join(', ')}) and frequency`,'integration|architect','integration'],
 ['Resilience','resilience','Resilience','Data centre mode, failover, RTO, RPO, DR test date and result, impact tolerance','resilience|continuity|infrastructure','resilience'],
 ['Strategy','strategy','Strategy','Pillars and initiatives, and the journeys, processes, capabilities and applications behind them','strategy|architect','strategy'],
 ['Regulation','regulation','Regulation','Requirements and article references that apply, with affected applications and size','compliance|risk','scenarios'],
 ['Change features and epics','change_backlog','Change_Backlog','Epics and features with what each changes: applications and change type, L3 capabilities, changed steps, drivers, dependencies, status and target quarter. You can also model a feature directly in the dashboard, or press Model what if on any application, supplier, capability, journey, step, process or initiative','delivery|portfolio|programme|change','change'],
 ['Scenarios','scenarios','Scenarios','Example scenarios added to the library and the Excel. Your own scenarios can also be saved directly in the dashboard','risk|resilience','scenarios'],
];
const GUIDE_ASKS=(()=>{const st=D.steps[0], reg=D.regulations[0], mig=D.apps.find(a=>a.time==='Migrate'||a.time==='Eliminate'), prev=(D.changelog[1]||D.changelog[0]||{}).version||'1.0';
 return [
 `Refresh the ${ORGS} EA atlas from the inbox.`,
 `Here is the latest supplier and contract register. Update procurement and show contracts with notice deadlines in the next 12 months${PG&&PG.completion?' or before '+PNAME+' completes':''}.`,
 reg?`Here are the ${reg.short||reg.name} requirements that apply to ${ORGS}. Replace the summary requirements and rerun the scenario.`:`Add the regulations that apply to ${ORGS} and map each requirement to the applications it affects.`,
 'Add a new process: describe it in one line, name the owner, and attach the steps and roles.',
 st?`For step ${st.id} (${st.name.toLowerCase()}), make a different role Accountable.`:'Change the Accountable role for a journey step.',
 mig?`We are replacing ${mig.name} next year. Update the application and show the impact.`:'We are replacing an application next year. Update it and show the impact.',
 'Here is our Jira epic and feature export. Load it into the change portfolio and list the features with blockers.',
 'Here is our technology org chart. Replace the illustrative technology roles.',
 `What changed between version ${prev} and the current version?`,
]})();
const GUIDE_RULES=[
 ['Do not edit the outputs','The dashboard and the Excel are rebuilt on every release, so edits made in them are lost. Change the model files instead. The one exception is saved scenarios and features, which live in the dashboard.'],
 ['Keep IDs stable','IDs such as A01, S04 or C05.04.02 never change and are never reused. New items get the next free ID.'],
 ['State the source','Say where each fact comes from. Confirmed facts are tagged Customer-provided and are never overwritten by a lower confidence value (Public, Partly confirmed, Illustrative).'],
 ['One Accountable per step','Every journey step must have exactly one Accountable role. A RACI change that breaks this is returned as a question.'],
 ['Retire, do not delete','Retired applications, roles and processes are marked retired and kept in the history, so the change log stays complete.'],
 ['Plain writing','British English, no em or en dashes, and no logos on the published dashboard.'],
];
const GUIDE_CADENCE=[
 ['Event driven',`Within a week of a material change: a new or retired system, a contract signed or exited, a major incident, a new regulation${PG?', a '+PDEC.toLowerCase():''}.`],
 ['Monthly','Licence consumption, contract renewals due in the next 12 months, DR test results, RACI changes.'],
 ['Quarterly','TIME ratings and health scores, capability maturity, strategy alignment, and a review of everything still marked Illustrative.'],
];
const GUIDE_OPEN=[
 ['Technology org chart','Replaces the illustrative technology roles','roles'],
 ...(D.regulations.length?[['Applicable regulatory requirements','Replaces the summary requirements with the ones that apply','scenarios']]:[]),
 ['Application inventory with TIME and health ratings','Replaces illustrative ratings and fills gaps','apps'],
 ['Supplier, contract and licence registers','Replaces illustrative commercial data and costs','licensing'],
 [`${ORGS} capability model`,`Aligns L1 to L3 names to ${ORGS}'s own model`,'capabilities'],
 ['Process maps and RACI from process owners','Confirms the journey steps and roles','pmap'],
 ['DR test register and BIA','Replaces illustrative RTO, RPO and test results','resilience'],
];
function guide(){
  const g=(D.changelog||[])[0]||{};
  const conf=['Customer-provided','Public','Partly confirmed','Illustrative'].map(c=>[c,D.apps.filter(a=>a.confidence===c).length]);
  const illus=conf.find(x=>x[0]==='Illustrative')[1];
  $('#view').innerHTML=`
  <section class="panel gd-hero"><div><h2>How this atlas is kept up to date</h2>
    <p class="sub" style="max-width:780px">The atlas is generated from one master dataset. To change it, you send new information in and a refresh produces a new version of the dashboard and the Excel together. You are looking at <b>version ${esc(D.meta.version)}</b>, released ${esc(D.meta.release_date)}. ${illus} of ${D.apps.length} applications are still Illustrative, so every update makes the atlas more accurate.</p></div>
    <div class="chips" style="align-self:flex-start"><button class="chip" data-view="changes">See the change log</button><button class="chip" data-view="glossary">Taxonomy & glossary</button></div></section>

  <h3 class="gd-h">1. Send new information in</h3>
  <div class="gd-cards">${GUIDE_ROUTES.map((r,i)=>`<article class="panel gd-card"><span class="gd-n">${i+1}</span><h4>${esc(r.t)}</h4><p>${esc(r.d)}</p><code>${esc(r.w)}</code></article>`).join('')}</div>

  <h3 class="gd-h">2. What happens next</h3>
  <ol class="gd-flow">${GUIDE_FLOW.map(([t,d],i)=>`<li><span class="gd-n">${i+1}</span><div><b>${esc(t)}</b><p>${esc(d)}</p></div></li>`).join('')}</ol>

  <h3 class="gd-h">3. Where each kind of update goes</h3>
  <section class="panel"><p class="sub">The suggested data owner sends or confirms the update. Owners are suggestions based on the roles in this atlas. Click a view to see where the change will show.</p>
   <div class="tbl-wrap"><table><thead><tr><th>Update</th>${CHAT?'':'<th>Inbox folder</th>'}<th>What changes</th><th>Suggested owner</th><th>Check in</th></tr></thead><tbody>
   ${GUIDE_TYPES.map(([t,f,tab,w,o,v])=>`<tr><td><b>${esc(t)}</b></td>${CHAT?'':`<td><code>inbox/${esc(f)}/</code></td>`}<td style="font-size:12.5px;min-width:260px">${esc(w)}</td><td>${(r=>r?chip('role',r,RO[r].name,false):'<span class="muted">To assign</span>')(roleLike(o))}</td><td><button class="chip" data-view="${v}">${esc(VIEWS.find(x=>x.id===v).name)}</button></td></tr>`).join('')}
   </tbody></table></div></section>

  <h3 class="gd-h">4. Things you can ask ${esc(AST)}</h3>
  <section class="panel"><p class="sub">Use these as they are or adapt them. Attach the file when there is one. Click to copy.</p>
   <div class="gd-asks">${GUIDE_ASKS.map(a=>`<button class="gd-ask" data-copy="${esc(a)}"><span>${esc(a)}</span><small>Copy</small></button>`).join('')}</div></section>

  <div class="gd-two">
   <section class="panel"><h3 class="gd-h" style="margin-top:0">5. Rules that keep it reliable</h3>
    <dl class="gd-dl">${GUIDE_RULES.map(([t,d])=>`<dt>${esc(t)}</dt><dd>${esc(d)}</dd>`).join('')}</dl></section>
   <section class="panel"><h3 class="gd-h" style="margin-top:0">6. Versions and releases</h3>
    <dl class="gd-dl">
     <dt>Numbering</dt><dd>Content changes raise the minor number (1.17 to 1.18). A change to the structure of the model raises the major number (2.0).</dd>
     <dt>What is recorded</dt><dd>Every release has release notes and a field-by-field comparison with the previous release, shown in the Change log and in the Change Log and Change Detail tabs of the Excel.</dd>
     <dt>Earlier versions</dt><dd>${CHAT?'Keep the dashboard, Excel and atlas file of each release under its version number if you need to go back.':(REPO?'Each release is a commit with the version in its message, and the files of each release are archived in <code>output/archive/v&lt;version&gt;/</code>.':'Each published version is labelled with its number in the page history, and the files of each release are archived in <code>output/archive/v&lt;version&gt;/</code>.')}</dd>
     <dt>Latest release</dt><dd>${g.version?`<button class="chip" data-view="changes">v${esc(g.version)}: ${esc(g.title)}</button>`:''}</dd>
    </dl></section>
  </div>

  <div class="gd-two">
   <section class="panel"><h3 class="gd-h" style="margin-top:0">7. Suggested review rhythm</h3>
    <dl class="gd-dl">${GUIDE_CADENCE.map(([t,d])=>`<dt>${esc(t)}</dt><dd>${esc(d)}</dd>`).join('')}</dl></section>
   <section class="panel"><h3 class="gd-h" style="margin-top:0">8. After a release</h3>
    <dl class="gd-dl">
     ${CHAT?'<dt>Dashboard file</dt><dd>Open it in any browser. Share it as a file, or upload it to SharePoint or an intranet site.</dd>':(REPO?"<dt>Dashboard file</dt><dd>In <code>output/</code>. Open it in any browser, or publish the folder to an internal site.</dd>":"<dt>Online dashboard</dt><dd>Republished at the same link, so bookmarks keep working. Share it from the page's Share menu.</dd>")}
     <dt>Intranet copy</dt><dd>Replace ${esc(PFX)}_EA_Dashboard.html wherever it is hosted. It works offline.</dd>
     <dt>Copilot agent</dt><dd>If you use one, overwrite its knowledge files with the same file names. The agent answers from the new version once they are indexed.</dd>
     <dt>EA tools</dt><dd>The Excel tabs are laid out for import into EA tools such as Archi, LeanIX, Ardoq, Sparx or ServiceNow APM.</dd>
    </dl></section>
  </div>

  <h3 class="gd-h">9. Most useful information to send next</h3>
  <section class="panel"><div class="tbl-wrap"><table><tbody>
   ${GUIDE_OPEN.map(([t,w,v])=>`<tr><td><b>${esc(t)}</b></td><td style="font-size:12.5px">${esc(w)}</td><td><button class="chip" data-view="${v}">${esc(VIEWS.find(x=>x.id===v).name)}</button></td></tr>`).join('')}
   </tbody></table></div></section>`;
  document.querySelectorAll('[data-copy]').forEach(b=>b.addEventListener('click',e=>{e.stopPropagation();const t=b.dataset.copy;const done=()=>{const s=b.querySelector('small');s.textContent='Copied';setTimeout(()=>{s.textContent='Copy'},1500)};
    try{navigator.clipboard.writeText(t).then(done,()=>{})}catch(err){try{const ta=document.createElement('textarea');ta.value=t;document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove();done()}catch(e2){}}}));
}
