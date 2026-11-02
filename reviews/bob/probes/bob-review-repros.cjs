const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = '/home/t3run/builder';
const ts = require(root + '/node_modules/typescript');
const vue = require(root + '/node_modules/vue');
const compile = (s) => ts.transpileModule(s, {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const defer = () => {let resolve,reject; const promise = new Promise((a,b)=>{resolve=a;reject=b}); return {promise,resolve,reject};};
function fixture() {
 const calls=[], notices=[], renders=[], timers=new Map(); let tid=0,mid=0;
 const route=vue.reactive({params:{pageId:'P'}});
 const builder={isAIEnabled:true,aiBuildingCanvas:false,aiEditEpoch:0,realtime:{on(){},off(){}}};
 const page={selectedPage:'P',pageLoadToken:0,savePage:async()=>{},setPage:async(...args)=>calls.push(['setPage',...args]),restoreSnapshot:async(...args)=>calls.push(['restoreSnapshot',...args])};
 const canvas={editingMode:'page',activeCanvas:{selectedBlocks:[]}};
 const f={calls,notices,renders,timers,builder,page,route,api:async(url,p)=>url.endsWith('get_ai_session')?{session_id:'A',messages:[]}:url.endsWith('run')?{session_id:'A',status:'accepted'}:[]};
 class Dispatcher {pendingAffectedBlocks=vue.ref([]);pendingAffectedScripts=vue.ref([]);reset(){};applyPageYaml(y){renders.push(y)};applyToolOperation(){};trackAffectedItem(){};mergeAffected(){}}
 const stubs={
  vue:{...vue,inject:(_,v)=>v},'vue-router':{useRoute:()=>route},'@vueuse/core':{useLocalStorage:()=>vue.ref('model')},
  'frappe-ui':{createResource:(o)=>({submit:async(p)=>{p=p??o.makeParams?.();calls.push([o.url,p]);return f.api(o.url,p);}}),toast:Object.fromEntries(['info','error','success'].map(k=>[k,(v)=>notices.push([k,v])]))},
  '@/stores/builderStore':{default:()=>builder},'@/stores/canvasStore':{default:()=>canvas},'@/stores/pageStore':{default:()=>page},
  '@/components/ai/toolDispatch':{ToolDispatcher:Dispatcher},'@/components/ai/realtime':{attachAIChatListeners(){},detachAIChatListeners(){}},
  '@/components/ai/yaml':{buildLocalMessage:(role,content,metadata)=>({id:'local-'+ ++mid,role,content,metadata})},
  '@/utils/helpers':{confirm:async()=>true,getErrorMessage:(_,s)=>s},'@/data/builderToken':{default:{reload(){}}}
 };
 const context={exports:{},require:(n)=>{if(!(n in stubs))throw Error('Unexpected import '+n);return stubs[n]},console,setTimeout:(fn,ms)=>{timers.set(++tid,{fn,ms});return tid},clearTimeout:(id)=>timers.delete(id),requestAnimationFrame:()=>1};
 vm.runInNewContext(compile(fs.readFileSync(root+'/frontend/src/components/AIChatController.ts','utf8')),context);
 f.chat=new context.exports.AIChatController(); f.chat.sessionId.value='A'; return f;
}
const tests=[];
function test(name,fn){tests.push([name,fn])}
test('Sending during a switch allows the stale load to replace the active turn',async()=>{
 const f=fixture(), d=defer(); f.api=async(u,p)=>u.endsWith('get_ai_session')?d.promise:u.endsWith('run')?{session_id:'A',status:'accepted'}:[];
 const switching=f.chat.switchSession('B');f.chat.prompt.value='Edit A';await f.chat.submitPrompt();
 assert.equal(f.calls.find(([u])=>u.endsWith('run'))[1].session_id,'A');
 d.resolve({session_id:'B',messages:[{id:'b',role:'user',content:'B history'}]});await switching;
 assert.equal(f.chat.sessionId.value,'B');assert.equal(f.chat.messages.value.length,1);assert.equal(f.chat.isSubmitting.value,true);
});
test('Completion reload drops a new turn started while that reload is pending',async()=>{
 const f=fixture(), d=defer();f.api=async(u)=>u.endsWith('get_ai_session')?d.promise:u.endsWith('run')?{session_id:'A'}:[];
 const done=f.chat.onComplete({session_id:'A',message:'done'});f.chat.prompt.value='Next edit';await f.chat.submitPrompt();assert.equal(f.chat.messages.value.length,2);
 d.resolve({session_id:'A',messages:[]});await done;assert.equal(f.chat.messages.value.length,0);assert.equal(f.chat.isSubmitting.value,true);
});
test('Refresh has no pending assistant to receive subsequent live text',async()=>{
 const f=fixture();f.chat.sessionId.value='';f.api=async(u)=>u.endsWith('get_ai_session')?{session_id:'A',messages:[{id:'u',role:'user',content:'build'}]}:[];
 await f.chat.mount();f.chat.onStream({session_id:'A',chunk:'Working on your brand'});
 assert.equal(f.chat.isSubmitting.value,true);assert.equal(f.chat.messages.value.length,1);assert.equal(f.chat.messages.value[0].role,'user');assert(!f.calls.some(([u])=>u.endsWith('get_active_build')));
});
test('Cancel watchdog claims a run is inactive without checking the server',async()=>{
 const f=fixture();f.chat.isSubmitting.value=true;f.api=async(u)=>u.endsWith('cancel')?{status:'ok'}:u.endsWith('get_ai_session')?{session_id:'A',messages:[]}:[];
 await f.chat.cancel();await [...f.timers.values()].find(t=>t.ms===20000).fn();
 assert.equal(f.chat.isSubmitting.value,false);assert(f.notices.some(([,m])=>m==='That run is no longer active.'));
});
test('Foreign-session completion retains the previous YAML stream offset',async()=>{
 const f=fixture();f.chat.onStream({session_id:'B',kind:'page_yaml',chunk:'old stream',offset:0});await f.chat.onComplete({session_id:'B'});
 f.chat.onStream({session_id:'B',kind:'page_yaml',chunk:'new stream',offset:0});assert.equal(f.chat.pageStreamContent.value,'old stream');
});
test('Python code-point offsets cause an emoji-following chunk to be dropped',()=>{
 const f=fixture();f.chat.onStream({session_id:'A',kind:'page_yaml',chunk:'😀',offset:0});f.chat.onStream({session_id:'A',kind:'page_yaml',chunk:'next',offset:1});assert.equal(f.chat.pageStreamContent.value,'😀');
});
test('Failed send restores text but loses attached image and block context',async()=>{
 const f=fixture();f.chat.imageData.value='data:image/png;base64,AA';f.chat.imagePreviewUrl.value='preview';f.chat.attachedBlocks.value=[{id:'hero',label:'Hero'}];f.chat.prompt.value='Use this image';f.api=async()=>{throw Error('offline')};
 await f.chat.submitPrompt();assert.equal(f.chat.prompt.value,'Use this image');assert.equal(f.chat.imageData.value,null);assert.equal(f.chat.attachedBlocks.value.length,0);
});
test('Confirmation response creates a phantom resumed turn in a different chat',async()=>{
 const f=fixture(),d=defer();f.api=async(u,p)=>u.endsWith('confirm_pending_settings')?d.promise:u.endsWith('get_ai_session')?{session_id:p.session_id||'A',messages:[]}:[];
 const confirmation=f.chat.confirmPendingAction({id:'card-A'},'apply');await f.chat.switchSession('B');d.resolve({resumed:true});await confirmation;
 assert.equal(f.chat.sessionId.value,'B');assert.equal(f.chat.isSubmitting.value,true);assert.equal(f.chat.messages.value[0].metadata.status,'running');
});
test('Revert still restores the page after transcript truncation rejects',async()=>{
 const f=fixture();f.api=async(u)=>{if(u.endsWith('revert_to_message'))throw Error('permission/connection');return {session_id:'A',messages:[]}};
 await f.chat.revertTurn({id:'m',metadata:{revertSnapshot:'snap'}});assert(f.calls.some(([u])=>u==='restoreSnapshot'));
});
function cardFixture(ui,answeredWith){
 const source=fs.readFileSync(root+'/frontend/src/components/ai/AIUISpec.vue','utf8').match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1];
 const answerModule={exports:{}};vm.runInNewContext(compile(fs.readFileSync(root+'/frontend/src/components/ai/cardAnswers.ts','utf8')),answerModule);
 const emits=[];const ctx={exports:{},require:(n)=> n==='vue'?vue:n==='./cardAnswers'?answerModule.exports:{},defineProps:()=>({ui,interactive:true,answeredWith,lead:'Pick a direction'}),defineEmits:()=> (...a)=>emits.push(a)};
 vm.runInNewContext(compile(source+'\nexport {steps, onOptionClick, submitCollected, hasInteractiveAtoms, isSingleQuestion};'),ctx);return {...ctx.exports,emits,answerModule};
}
test('Multi-question form loses the picked photo URL in the submitted reply',()=>{
 const f=cardFixture([{kind:'choices',label:'Photo',options:[{label:'Cafe',image:'https://example.test/cafe.jpg'}]},{kind:'input',label:'Name'},{kind:'actions',buttons:[{label:'Build'}]}]);
 f.onOptionClick(0,{kind:'choices'},0,{label:'Cafe',image:'https://example.test/cafe.jpg'});f.submitCollected('Build');assert(!f.emits[0][1].includes('https://'));assert(f.emits[0][1].includes('Cafe'));
});
test('A multi-select-only card suppresses fallback without providing a submit action',()=>{
 const f=cardFixture([{kind:'choices',label:'Sections',multi:true,options:[{label:'Menu'}]}]);f.onOptionClick(0,{kind:'choices',multi:true},0,{label:'Menu'});
 assert.equal(f.hasInteractiveAtoms.value,true);assert.equal(f.emits.length,0);
});
test('Upload escape hatch is grouped with the next question, not its photo choices',()=>{
 const f=cardFixture([{kind:'choices',label:'Photo',options:[{label:'Cafe'}]},{kind:'upload',label:'Your photo'},{kind:'input',label:'Brand'},{kind:'actions',buttons:[{label:'Build'}]}]);
 assert.equal(JSON.stringify(f.steps.value),JSON.stringify([[0],[1,2,3]]));
});
test('Free-text answer is truncated at a colon then marked fully represented',()=>{
 const f=cardFixture([]);const out=f.answerModule.exports.cardAnswers([{kind:'choices',label:'Direction',options:[{label:'Poster'}]}],'Poster, but change this: keep all prices in euros','Direction');
 assert.equal(out[0].answer,'Poster, but change this');assert.equal(out.length,1);
});
(async()=>{let failed=0;for(const [name,fn]of tests){try{await fn();console.log('REPRODUCED '+name)}catch(e){failed++;console.error('FAILED '+name+'\n'+e.stack)}}console.log(`${tests.length-failed}/${tests.length} defect reproductions passed (mocked dependencies; no network or site writes)`);process.exitCode=failed?1:0;})();
