// Runs the example scenarios and the change backlog through the engines for the Excel.
//   node compute_scenarios.js path/to/ea-atlas
const path=require('path'), fs=require('fs');
const WS=path.resolve(process.argv[2]||'.'), REPO=path.join(WS,'repository');
const E=require('./scenario_engine.js'); const D=JSON.parse(fs.readFileSync(path.join(REPO,'data.json'),'utf8'));
const out=D.example_scenarios.map(sc=>{const r=E.run(D,sc);return {id:sc.id,
 name:sc.name,type:E.TYPES[sc.type].label,disruptive:E.TYPES[sc.type].disruptive,likelihood:sc.likelihood||null,
 level:r.level,risk:sc.likelihood&&E.TYPES[sc.type].disruptive?E.riskRating(r.level,sc.likelihood):'',
 primary:r.primary.length,degraded:Object.keys(r.degraded).length+Object.keys(r.atRisk).length,crit:r.crit,tier0:r.tier0,
 journeys:r.journeys.length,steps:r.steps.length,caps:r.caps.length,procs:r.procs.length,ifs:r.ifs.length,
 rto:r.slowestRto?r.slowestRto.hours:null,cost_at_stake:+r.costAtStake.toFixed(2),cost_delta:+r.costDelta.toFixed(2),reqs:r.reqs.length,effort:r.effort,
 apps:r.all.map(a=>({app:a,effect:r.down[a]?'Down':r.changed[a]?'Changes':r.degraded[a]?'Degraded':'At risk',reason:r.down[a]||r.changed[a]||r.degraded[a]||r.atRisk[a]})),
 description:sc.description||'',mitigation:sc.mitigation||''}});
fs.writeFileSync(path.join(REPO,'scenario_results.json'),JSON.stringify(out));console.log('scenarios',out.length,out.map(x=>x.id+':'+x.level).join(' '));
const F=require('./feature_engine.js');
const fo=D.features.map(f=>{const r=F.run(D,f,D.features);return {id:f.id,epic:f.epic,name:f.name,status:f.status,target:f.target,size:f.size,owner:f.owner,level:r.level,score:r.score,
 apps:r.direct.map(x=>x.app+' '+x.change),partners:r.partners.map(p=>({app:p.app,action:p.action,ifs:p.ifs.length})),journeys:r.journeys,steps_changed:r.stepsChanged,steps_touched:r.stepsTouched.length,
 procs:r.procs,caps3:r.caps3,retrain:r.retrain,inform:r.inform,customer_facing:r.customerFacing,domains:r.domains.map(d=>d.id),sups:r.sups.map(s=>s.sup),tier01:r.tier01,crit:r.crit,
 contention:r.contention.map(c=>c.feature),flags:r.flags}});
const eo=D.epics.map(e=>{const r=F.epic(D,e,D.features);return {id:e.id,level:r.level,score:r.score,apps:r.direct.length,partners:r.partners.length,journeys:r.journeys.length,retrain:r.retrain.length,first:r.first,last:r.last,issues:r.flags.length}});
fs.writeFileSync(path.join(REPO,'feature_results.json'),JSON.stringify({features:fo,epics:eo}));
const lv={}; fo.forEach(x=>lv[x.level]=(lv[x.level]||0)+1); console.log('features',fo.length,JSON.stringify(lv));
