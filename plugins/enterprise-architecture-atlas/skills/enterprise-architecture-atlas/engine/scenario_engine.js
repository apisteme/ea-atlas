/* Atlas scenario impact engine. Pure functions over the repository data; nothing here is specific to an organisation.
   Used inline by the dashboard and by node to compute Excel results. */
var ScenarioEngine = (function(){
  var TYPES = {
    app_outage:      {label:'Application outage', target:'app', disruptive:true,  help:'One or more applications become unavailable.'},
    platform_failure:{label:'Platform failure',   target:'platform', disruptive:true, help:'A shared platform fails: hosting, virtualisation, container, messaging, events, API gateway or database.'},
    supplier_failure:{label:'Supplier failure or exit', target:'sup', disruptive:true, help:'A supplier stops providing service, through failure, dispute or forced exit.'},
    dc_loss:         {label:'Data centre loss',   target:'dc', disruptive:true,  help:'A data centre becomes unavailable.'},
    decommission:    {label:'Replace or decommission', target:'app', disruptive:false, help:'Applications are retired or replaced. Shows what must be redesigned, re-integrated and migrated.'},
    price_change:    {label:'Supplier price change', target:'sup', disruptive:false, help:'A supplier changes its prices. Shows the cost effect and what is exposed.'},
    regulatory_change:{label:'Regulatory change', target:'requirement', disruptive:false, help:'A new regulation or rule. Each requirement is mapped to the applications, capabilities and processes that must change.'}
  };
  function platformIds(D){ return D.apps.filter(function(a){return a.platform}).map(function(a){return a.id}) }
  var LIKELIHOOD = ['','Rare','Unlikely','Possible','Likely','Almost certain'];
  var LEVELS = ['Low','Medium','High','Critical'];
  var SIZE_POINTS = {S:1, M:3, L:8};

  function idx(D){
    if (D.__idx) return D.__idx;
    var I = {AP:{},ST:{},VS:{},CVS:{},SU:{},RES:{},LIC:{},SUP:{},K:{}};
    D.apps.forEach(function(a){I.AP[a.id]=a});
    D.steps.forEach(function(s){I.ST[s.id]=s});
    D.value_streams.forEach(function(v){I.VS[v.id]=v});
    D.customer_value_streams.forEach(function(c){I.CVS[c.id]=c});
    D.suppliers.forEach(function(s){I.SU[s.id]=s});
    (D.resilience||[]).forEach(function(r){I.RES[r.app]=r});
    D.licences.forEach(function(l){I.LIC[l.app]=l});
    D.support.forEach(function(s){I.SUP[s.app]=s});
    D.contracts.forEach(function(k){I.K[k.supplier]=k});
    I.appSteps={}; D.apps.forEach(function(a){I.appSteps[a.id]=[]});
    D.steps.forEach(function(s){s.apps.forEach(function(a){I.appSteps[a].push(s.id)})});
    I.appSups={}; D.apps.forEach(function(a){I.appSups[a.id]=[]});
    D.app_supplier.forEach(function(x){I.appSups[x.app].push(x)});
    Object.defineProperty(D,'__idx',{value:I,enumerable:false});
    return I;
  }
  function cost(I,id){return ((I.LIC[id]||{}).annual_cost_m||0)+((I.SUP[id]||{}).annual_support_cost_m||0)}
  function uniq(a){var o=[];a.forEach(function(x){if(o.indexOf(x)<0)o.push(x)});return o}

  function run(D, sc){
    var I = idx(D), T = TYPES[sc.type] || TYPES.app_outage;
    var targets = sc.targets || [];
    var down = {}, degraded = {}, atRisk = {}, changed = {}, notes = [];
    function mark(map, id, why){ if(!I.AP[id]) return false; if(down[id]||changed[id]) return false; if(map===degraded&&(atRisk[id])) {} if(map[id]) return false; map[id]=why; return true; }

    if (sc.type==='app_outage' || sc.type==='platform_failure') {
      targets.forEach(function(id){ mark(down,id,'Directly affected') });
    }
    if (sc.type==='supplier_failure') {
      targets.forEach(function(sid){
        D.app_supplier.filter(function(x){return x.supplier===sid}).forEach(function(x){
          if (/AMS|SI|Integration|Agency/i.test(x.role) && !/Product|In-house|Hosting|Virtualisation|Container|Platform|Scheme/i.test(x.role)) mark(degraded,x.app,(I.SU[sid]||{}).name+' provides '+x.role+'; change and support at risk');
          else mark(down,x.app,(I.SU[sid]||{}).name+' is '+x.role.toLowerCase());
        });
      });
    }
    if (sc.type==='dc_loss') {
      var DCS = D.data_centres||[], model = (D.meta||{}).dc_model||'single';
      var P1 = DCS.filter(function(d){return d.kind==='primary'})[0]||DCS[0], P2 = DCS.filter(function(d){return d.kind==='secondary'})[0]||DCS[1];
      var lostP = P1 && targets.indexOf(P1.id)>=0, lostS = P2 && targets.indexOf(P2.id)>=0;
      D.apps.forEach(function(a){
        if (a.site!=='internal') return;
        if (model==='active-active') {
          if (lostP && lostS) mark(down,a.id,'Both sites lost');
          else if (lostP || lostS) mark(atRisk,a.id,'Runs on one site only until '+(lostP?P1.name:P2.name)+' is restored');
        } else if (model==='active-passive' && P2) {
          if (lostP) mark(down,a.id,'Runs live in '+P1.name+'; needs site failover to '+P2.name);
          else if (lostS) mark(atRisk,a.id,'Loses its '+P2.name+' standby; no site failover available');
        } else if (lostP) mark(down,a.id,'Runs in '+P1.name+'; restore from backup');
      });
      if (model==='active-passive' && P2) {
        if (lostP) notes.push('Active-passive: every in-house application is down until the site failover to '+P2.name+' completes. Recovery time is set by the failover runbook and the slowest critical application.');
        if (lostS && !lostP) notes.push('No immediate outage. '+P1.name+' keeps running, but there is no secondary site until '+P2.name+' is restored, so any failure in that window has no recovery path.');
      } else if (model==='active-active' && (lostP||lostS)) notes.push('Active-active: the remaining site carries the load. Check capacity and that every critical application is deployed on both sites.');
      else if (lostP) notes.push('Single site: in-house applications must be rebuilt and restored from backup elsewhere. Recovery is likely to exceed most recovery targets.');
    }
    if (sc.type==='decommission') {
      targets.forEach(function(id){ if(I.AP[id]) changed[id]='Retired or replaced' });
    }
    if (sc.type==='price_change') {
      targets.forEach(function(sid){
        D.apps.filter(function(a){return a.vendor===sid}).forEach(function(a){ changed[a.id]='Licence and support repriced' });
      });
    }

    // dependency propagation (outage types only)
    if (T.disruptive && sc.type!=='dc_loss') {
      var grew = true, guard = 0;
      while (grew && guard++ < 10) {
        grew = false;
        Object.keys(down).forEach(function(p){
          D.apps.forEach(function(a){
            (a.runs_on||[]).forEach(function(r){ if (r.app===p && mark(down,a.id,'Runs on '+I.AP[p].name)) grew = true; });
          });
          var hosts = ((I.AP[p].platform||{}).hosts)||[];
          if (hosts.length) D.apps.forEach(function(a){
            if (hosts.some(function(h){return (a.hosting||'').indexOf(h)===0}) && a.id!==p && mark(down,a.id,'Hosted on '+I.AP[p].name)) grew = true;
          });
        });
      }
      D.apps.forEach(function(pa){
        var c = (pa.platform||{}).carries; if (!c || !down[pa.id]) return;
        var re = new RegExp(c,'i');
        D.interfaces.forEach(function(i){
          if (re.test(i.protocol)) [i.source_app,i.target_app].forEach(function(x){ mark(degraded,x,'Loses '+pa.name+' flow: '+i.data) });
        });
      });
      D.apps.forEach(function(pa){ var n=(pa.platform||{}).note; if (n && down[pa.id]) notes.push(n); });
      // one hop of interface impact
      D.interfaces.forEach(function(i){
        if (down[i.source_app] && !down[i.target_app]) mark(degraded,i.target_app,'No data from '+I.AP[i.source_app].name+' ('+i.data+')');
        if (down[i.target_app] && !down[i.source_app]) mark(degraded,i.source_app,'Cannot reach '+I.AP[i.target_app].name+' ('+i.data+')');
      });
    }
    if (sc.type==='decommission') {
      D.apps.forEach(function(a){ (a.runs_on||[]).forEach(function(r){ if(changed[r.app]) mark(atRisk,a.id,'Must be re-hosted: runs on '+I.AP[r.app].name) }) });
      D.interfaces.forEach(function(i){
        if (changed[i.source_app] && !changed[i.target_app]) mark(degraded,i.target_app,'Interface to rework: '+i.data);
        if (changed[i.target_app] && !changed[i.source_app]) mark(degraded,i.source_app,'Interface to rework: '+i.data);
      });
    }

    var reqs = [], reqCaps = [], reqProcs = [], effort = 0, reg = null;
    if (sc.type==='regulatory_change') {
      reg = (D.regulations||[]).filter(function(r){return r.id===sc.regulation})[0] || (D.regulations||[])[0];
      if (reg) {
        reqs = reg.requirements.filter(function(q){return !targets.length || targets.indexOf(q.id)>=0});
        reqs.forEach(function(q){
          q.apps.forEach(function(a){ if(!I.AP[a]) return; changed[a] = changed[a] ? changed[a]+'; '+q.id : q.id+' '+q.short });
          reqCaps = reqCaps.concat(q.caps); reqProcs = reqProcs.concat(q.procs); effort += SIZE_POINTS[q.size]||0;
        });
      }
    }
    var primary = Object.keys(down).concat(Object.keys(changed));
    var all = uniq(primary.concat(Object.keys(degraded)).concat(Object.keys(atRisk)));
    var stepsHit = uniq(primary.reduce(function(acc,a){return acc.concat(I.appSteps[a]||[])},[]));
    var stepsDeg = uniq(Object.keys(degraded).concat(Object.keys(atRisk)).reduce(function(acc,a){return acc.concat(I.appSteps[a]||[])},[])).filter(function(s){return stepsHit.indexOf(s)<0});
    var steps = stepsHit.concat(stepsDeg);
    var journeys = uniq(steps.map(function(s){return I.ST[s].vs}));
    var cvs = uniq(journeys.map(function(v){return I.VS[v].parent}));
    var caps = sc.type==='regulatory_change' ? uniq(reqCaps) : uniq(all.reduce(function(acc,a){return acc.concat(I.AP[a].capabilities)},[]));
    var procs = sc.type==='regulatory_change' ? uniq(reqProcs) : D.business_processes.filter(function(b){return b.level===2 && b.apps.some(function(a){return all.indexOf(a)>=0})}).map(function(b){return b.id});
    var roles = uniq(stepsHit.reduce(function(acc,s){var t=I.ST[s];return acc.concat(t.R,[t.A],t.C)},[]));
    var ifs = D.interfaces.filter(function(i){return primary.indexOf(i.source_app)>=0||primary.indexOf(i.target_app)>=0}).map(function(i){return i.id});
    var sups = uniq(all.reduce(function(acc,a){return acc.concat(I.appSups[a].map(function(x){return x.supplier}))},[]));
    var critical = primary.filter(function(a){return I.AP[a].tier_n<=1});
    var rtoPool = (sc.type==='dc_loss'||sc.type==='app_outage'||sc.type==='platform_failure'||sc.type==='supplier_failure') ? primary.filter(function(a){return I.AP[a].tier_n<=1 && I.RES[a]}) : [];
    var slow = rtoPool.reduce(function(w,a){return !w||I.RES[a].rto_hours>I.RES[w].rto_hours?a:w},null);
    var drIssues = primary.filter(function(a){return I.RES[a] && /Failed|issues|Not tested/.test(I.RES[a].dr_result)});
    var costAtStake = primary.reduce(function(t,a){return t+cost(I,a)},0);
    var costDelta = 0;
    if (sc.type==='price_change') costDelta = costAtStake * (Number(sc.pct)||0)/100;
    if (sc.type==='decommission') costDelta = -costAtStake;

    var crit = primary.filter(function(a){return I.AP[a].crit}).length;
    var cifDeg = Object.keys(degraded).concat(Object.keys(atRisk)).filter(function(a){return I.AP[a].crit}).length;
    var tier0 = primary.filter(function(a){return I.AP[a].tier_n===0}).length;
    var vsCount = cvs.filter(function(c){return !(I.CVS[c]||{}).cross_cutting}).length;
    var score, level;
    if (sc.type==='price_change') {
      var total = D.apps.reduce(function(t,a){return t+cost(I,a.id)},0)||1, m = Math.abs(costDelta)/total;
      level = m>=0.05?'Critical':m>=0.025?'High':m>=0.006?'Medium':'Low'; score = Math.round(m*1000);
    } else {
      var tier0Deg = Object.keys(degraded).filter(function(a){return I.AP[a].tier_n===0}).length;
      score = tier0*12 + crit*2 + cifDeg + tier0Deg*3 + vsCount*3 + journeys.length;
      if (sc.type==='dc_loss' && Object.keys(down).length===0) score = Math.round(score/3);
      level = score>=45?'Critical':score>=22?'High':score>=9?'Medium':'Low';
    }
    return {
      type:sc.type, typeLabel:T.label, disruptive:T.disruptive,
      down:down, degraded:degraded, atRisk:atRisk, changed:changed,
      primary:primary, all:all, steps:steps, stepsHit:stepsHit, journeys:journeys, cvs:cvs, caps:caps, procs:procs, roles:roles,
      ifs:ifs, sups:sups, critical:critical, crit:crit, critDegraded:cifDeg, tier0:tier0, valueStreams:vsCount,
      slowestRto: slow ? {app:slow, hours:I.RES[slow].rto_hours} : null, drIssues:drIssues,
      costAtStake:costAtStake, costDelta:costDelta, score:score, level:level, notes:notes,
      reqs:reqs.map(function(q){return q.id}), effort:effort, regulation:reg?reg.id:null
    };
  }
  function riskRating(level, likelihood){
    var l = Number(likelihood)||0, i = LEVELS.indexOf(level)+1;
    var r = l*i; return r>=12?'Critical':r>=8?'High':r>=4?'Medium':'Low';
  }
  return {TYPES:TYPES, platformIds:platformIds, LIKELIHOOD:LIKELIHOOD, LEVELS:LEVELS, run:run, riskRating:riskRating, cost:function(D,id){return cost(idx(D),id)}};
})();
if (typeof module!=='undefined') module.exports = ScenarioEngine;
