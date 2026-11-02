// Real TS modules transpiled in memory. Fake canvas/DOM/network; no app or site writes.
const fs = require('fs');
const ts = require('/home/t3run/builder/node_modules/typescript');
const vue = require('/home/t3run/builder/node_modules/vue');
const root = '/home/t3run/builder/';
function moduleAt(path, dependencies) {
  const js = ts.transpileModule(fs.readFileSync(root + path, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }}).outputText;
  const exports = {};
  new Function('exports', 'require', js)(exports, name => {
    if (name in dependencies) return dependencies[name];
    throw new Error('Unexpected dependency: ' + name);
  });
  return exports;
}
(async () => {
  const results = {};
  const normal = moduleAt('frontend/src/components/ai/normalizeStyles.ts', {'@/utils/helpers': {kebabToCamelCase: s => s.replace(/-([a-z])/g, (_,c)=>c.toUpperCase())}});
  const { ToolDispatcher } = moduleAt('frontend/src/components/ai/toolDispatch.ts', {
    'vue': vue, './normalizeStyles': normal,
    './yaml': { STANDARD_ATTRS: new Set(['src', 'alt', 'href']), bindingEntry: () => ({}) },
    '@/utils/block/tree': { findBlockInTree: (id, roots) => {
      const visit = b => b.blockId === id ? b : (b.children || []).map(visit).find(Boolean);
      return roots.map(visit).find(Boolean);
    } },
    '@/utils/helpers': { getBlockInstance: b => b }
  });
  const title = { blockId: 'title', element: 'h1', innerHTML: 'old', baseStyles: {}, mobileStyles: {}, tabletStyles: {}, attributes: {}, customAttributes: {}, dynamicValues: [], setInnerHTML(value) { this.innerHTML = value; } };
  const page = { blockId: 'root', children: [title] };
  const dispatcher = new ToolDispatcher({}, { value: { getRootBlock: () => page } });
  const op = JSON.parse(fs.readFileSync('/tmp/bob-review-rejected-op.json'));
  dispatcher.applyToolOperation(op.tool_name, op.args);
  results.rejected_bulk_client_html = title.innerHTML;
  dispatcher.applyToolOperation('update_block', { block_id: 'title', element: 'script' });
  results.forbidden_element_client = title.element;

  const registryModule = moduleAt('frontend/src/utils/createRegistry.ts', {vue});
  const registry = registryModule.createRegistry();
  const bad = { default: { install() { registry.register({name: 'partial'}); throw new Error('fixture fail'); } } };
  const loader = moduleAt('frontend/src/plugins/loader.ts', {
    vue,
    '@/utils/createRegistry': registryModule,
    './context': { createPluginContext: p => ({name:p.name}) },
    'fixture-bad': bad
  });
  loader.installPlugins({}, [{plugin:{name:'bob/fixture', entryUrl:'old'}, vuePlugin:{ install(){registry.register({name:'original'});} }}]);
  try { await loader.replacePlugin({name:'bob/fixture', entryUrl:'fixture-bad'}); } catch (e) { results.plugin_replace_error = e.message; }
  results.plugin_replace_remaining_items = registry.all.value.map(x=>x.name);
  results.plugin_replace_running_entry = loader.getRunningEntry('bob/fixture');
  loader.installPlugins({}, [{plugin:{name:'bob/async',entryUrl:'async'}, vuePlugin:{async install(){await Promise.resolve();registry.register({name:'late'});}}}]);
  await Promise.resolve();
  loader.unloadPlugin('bob/async');
  results.async_registration_survives_unload = registry.all.value.some(x=>x.name==='late');

  const listeners = {};
  const inputs = [
    {name:'name',value:'Ada',type:'text'},
    {name:'email',value:'invalid-email',type:'email'},
    {name:'consent',value:'on',type:'checkbox',checked:false},
    {name:'plan',value:'pro',type:'radio',checked:true},
    {name:'plan',value:'basic',type:'radio',checked:false},
  ];
  const button = {textContent:'Send',addEventListener:(name,fn)=>listeners[name]=fn};
  let validityChecks = 0;
  const form = {tagName:'FORM',querySelectorAll:()=>inputs,querySelector:q=>q.startsWith('button')?button:inputs[0],addEventListener:()=>{},checkValidity:()=>{validityChecks++;return false;}};
  const document = {readyState:'complete',querySelector:()=>form};
  let body;
  const fetch = (url, options) => {body=JSON.parse(options.body);return Promise.resolve({ok:true,json:()=>Promise.resolve({})});};
  new Function('document','fetch',fs.readFileSync('/tmp/bob-review-form.js','utf8'))(document,fetch);
  listeners.click({preventDefault(){}});
  await Promise.resolve(); await Promise.resolve();
  results.form_submission = body;
  results.form_validity_checks = validityChecks;
  fs.writeFileSync('/tmp/bob-review-probes-js.json',JSON.stringify(results,null,2));
  console.log(JSON.stringify(results,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
