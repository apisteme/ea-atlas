// Headless smoke test for a built dashboard. Needs jsdom (npm install jsdom).
//   node smoke_test.js path/to/<prefix>_EA_Dashboard.html
// Opens every view, every drawer type, every lens and colour mode, the What if? builder (create, save,
// delete for every scenario type), the compare tab, the Change impact backlog, roadmap, portfolio and
// feature builder (create, save, delete), and every Model what if option, then reports console errors.
const fs = require('fs');
const { JSDOM, VirtualConsole } = require('jsdom');
const file = process.argv[2];
if (!file) { console.error('usage: node smoke_test.js dashboard.html'); process.exit(2); }
const errors = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => errors.push('jsdomError: ' + (e.message || e) + (e.detail ? ' ' + (e.detail.stack || e.detail) : '')));
vc.on('error', (...a) => errors.push('console.error: ' + a.join(' ')));
const html = fs.readFileSync(file, 'utf8');
const dom = new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true, url: 'https://example.test/atlas.html', virtualConsole: vc });
const w = dom.window;
w.scrollTo = () => {}; w.HTMLElement.prototype.scrollIntoView = () => {};
w.requestAnimationFrame = cb => setTimeout(cb, 0);
w.navigator.clipboard = { writeText: () => Promise.resolve() };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const $ = s => w.document.querySelector(s), $$ = s => [...w.document.querySelectorAll(s)];
const click = el => el && el.dispatchEvent(new w.MouseEvent('click', { bubbles: true, cancelable: true }));
const change = (el, v) => { if (!el) return; el.value = v; el.dispatchEvent(new w.Event('change', { bubbles: true })); };
let steps = 0;
function step(label, fn) { try { fn(); steps++; } catch (e) { errors.push(label + ': ' + (e.stack || e)); } }
async function astep(label, fn) { try { await fn(); steps++; } catch (e) { errors.push(label + ': ' + (e.stack || e)); } }
(async () => {
  await sleep(100);
  const D = w.eval('D');
  const views = $$('#nav button[data-view]').map(b => b.dataset.view);
  for (const v of views) step('view ' + v, () => { w.eval(`go(${JSON.stringify(v)})`); if (!$('#view').innerHTML.trim()) throw new Error('empty view ' + v); });
  // lenses and modes
  step('capability lenses', () => { w.eval("go('capabilities')"); $$('[data-lens]').map(b => b.dataset.lens).forEach(k => { click($(`[data-lens="${k}"]`)); }); click($('[data-capl3]')); click($('[data-capl3]')); });
  step('landscape modes', () => { w.eval("go('landscape')"); $$('[data-land]').map(b => b.dataset.land).forEach(k => click($(`[data-land="${k}"]`))); });
  step('integration focus', () => { w.eval("go('integration')"); const n = $('[data-ifocus]'); click(n); $$('[data-ifam]').slice(0, 2).forEach(click); click($('[data-iall]')); });
  step('resilience filters', () => { w.eval("go('resilience')"); $$('[data-resf]').map(b => b.dataset.resf).forEach(k => click($(`[data-resf="${k}"]`))); });
  step('value streams', () => { w.eval("go('processes')"); $$('[data-cvs]').map(b => b.dataset.cvs).forEach(k => click($(`[data-cvs="${k}"]`))); });
  step('process maps', () => { D.value_streams.forEach(v => { w.eval(`state.pmapVs=${JSON.stringify(v.id)};go('pmap')`); }); });
  step('apps filters', () => { w.eval("go('apps')"); $$('[data-sort]').slice(0, 4).forEach(click); click($('[data-nav="apps|reset=1"]')); });
  step('glossary', () => { w.eval("go('glossary')"); click($('[data-gcat]')); });
  // drawers
  const ent = [];
  D.apps.forEach(a => ent.push(['app', a.id])); D.suppliers.forEach(s => ent.push(['sup', s.id]));
  D.capabilities.filter(c => c.parent).forEach(c => ent.push(['cap', c.id])); (D.capabilities_l3 || []).slice(0, 40).forEach(c => ent.push(['cap', c.id]));
  D.steps.forEach(s => ent.push(['step', s.id])); D.roles.forEach(r => ent.push(['role', r.id]));
  D.business_processes.forEach(b => ent.push(['bp', b.id])); D.customer_value_streams.forEach(c => ent.push(['cvs', c.id]));
  D.value_streams.forEach(v => ent.push(['vs', v.id])); D.glossary.slice(0, 10).forEach(g => ent.push(['term', g.id]));
  D.strategy.initiatives.forEach(i => ent.push(['si', i.id])); (D.features || []).forEach(f => ent.push(['feat', f.id])); (D.epics || []).forEach(e => ent.push(['epic', e.id]));
  ent.forEach(([t, i]) => step(`drawer ${t}:${i}`, () => { w.eval(`openEnt(${JSON.stringify(t)},${JSON.stringify(i)})`); w.eval('closeDrawer()'); }));
  if (D.programme) (D.programme.decisions || []).forEach(d => step('decision ' + d.id, () => { w.eval(`go('programme');openDec(${JSON.stringify(d.id)})`); w.eval('closeDrawer()'); }));
  if (D.programme) step('programme lens filters', () => { w.eval("go('programme')"); $$('[data-blens]').slice(0, 6).forEach(click); });
  // trace
  step('trace', () => { w.eval("go('trace')"); $$('[data-trace]').slice(0, 5).forEach(click); });
  // What if: show every example, compare tab, builder per type
  await astep('scenarios library', async () => { w.eval("go('scenarios')"); for (const s of D.example_scenarios) { w.eval(`scShow(${JSON.stringify(s.id)})`); } const tabs = $$('[data-sctab]'); tabs.forEach(click); });
  const types = Object.keys(w.eval('ScenarioEngine.TYPES'));
  for (const ty of types) {
    await astep('scenario builder ' + ty, async () => {
      w.eval("go('scenarios');scOpenEditor(scBlank())");
      $('#sc-name').value = 'Smoke ' + ty;
      change($('#sc-type'), ty);
      const add = $('#sc-add'); if (add && add.options.length > 1) { add.value = add.options[1].value; click($('[data-scadd]')); }
      const dc = $('[data-scdc]'); if (dc) { dc.checked = true; dc.dispatchEvent(new w.Event('change', { bubbles: true })); }
      click($('[data-scsave]')); await sleep(30);
      const saved = w.eval('ScStore.items').find(x => x.name === 'Smoke ' + ty);
      if (!saved) throw new Error('scenario not saved for ' + ty + ': ' + ($('#sc-formmsg') || {}).textContent);
      w.eval(`scOpenEditor(scFind(${JSON.stringify(saved.id)}))`);
      const del = $(`[data-scdel="${saved.id}"]`); click(del); click($(`[data-scdel="${saved.id}"]`)); await sleep(30);
      if (w.eval('ScStore.items').some(x => x.id === saved.id)) throw new Error('scenario not deleted ' + ty);
    });
  }
  // Change impact
  await astep('change tabs', async () => { w.eval("go('change')"); $$('[data-fttab]').map(b => b.dataset.fttab).forEach(k => click($(`[data-fttab="${k}"]`))); click($('[data-fttab="backlog"]')); (D.epics || []).forEach(e => w.eval(`state.ftSel=${JSON.stringify(e.id)};change()`)); });
  await astep('feature builder', async () => {
    w.eval("go('change');ftOpenEditor(ftBlank())");
    $('#ft-name').value = 'Smoke feature'; $('#ft-name').dispatchEvent(new w.Event('input', { bubbles: true }));
    const a = $('#ft-addapps'); a.value = a.options[1].value; click($('[data-ftadd="apps"]'));
    const c = $('#ft-addcaps'); if (c && c.querySelector('option[value^="C"]')) { c.value = c.querySelector('option[value^="C"]').value; click($('[data-ftadd="caps"]')); }
    const s = $('#ft-addsteps'); if (s && s.querySelector('option[value*="."]')) { s.value = s.querySelector('option[value*="."]').value; click($('[data-ftadd="steps"]')); }
    click($('[data-ftsave]')); await sleep(30);
    const f = w.eval('FtStore.items').find(x => x.name === 'Smoke feature'); if (!f) throw new Error('feature not saved');
    w.eval(`state.ftSel=${JSON.stringify(f.id)};change()`);
    w.eval(`ftOpenEditor(ftFind(${JSON.stringify(f.id)}))`);
    click($(`[data-ftdel="${f.id}"]`)); click($(`[data-ftdel="${f.id}"]`)); await sleep(30);
    if (w.eval('FtStore.items').some(x => x.id === f.id)) throw new Error('feature not deleted');
  });
  // Model what if from drawers
  const wi = [['app', D.apps[0].id], ['app', (D.apps.find(a => a.platform) || D.apps[0]).id], ['sup', D.suppliers.find(s => !s.internal).id], ['cap', D.capabilities.find(c => c.parent).id], ['step', D.steps[0].id], ['vs', D.value_streams[0].id], ['bp', D.business_processes.find(b => b.parent).id]];
  if (D.strategy.initiatives.length) wi.push(['si', D.strategy.initiatives[0].id]);
  for (const [t, i] of wi) {
    const opts = w.eval(`wiOptions(${JSON.stringify(t)},${JSON.stringify(i)})`).map(o => o.k);
    for (const k of opts) await astep(`what if ${t}:${i} ${k}`, async () => { w.eval(`wiGo(${JSON.stringify(k)},${JSON.stringify(t)},${JSON.stringify(i)})`); await sleep(5); w.eval('scDraft=null;ftDraft=null;closeDrawer()'); });
  }
  // search
  step('search', () => { const q = $('#q'); q.value = D.apps[0].name.slice(0, 4); q.dispatchEvent(new w.Event('input', { bubbles: true })); click($('#results [data-ent]')); w.eval('closeDrawer()'); });
  await sleep(50);
  console.log(`steps ${steps}, errors ${errors.length}`);
  errors.slice(0, 25).forEach(e => console.log(' -', e.slice(0, 600)));
  process.exit(errors.length ? 1 : 0);
})();
