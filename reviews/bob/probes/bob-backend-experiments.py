"""Offline, synthetic read-only probes of the checked-out Bob backend."""
import os
os.environ['LITELLM_LOCAL_MODEL_COST_MAP'] = 'True'
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/home/t3run/builder')
import socket
def offline(*args, **kwargs):
    raise RuntimeError('Offline review: networking disabled')
socket.socket.connect = offline
socket.socket.connect_ex = offline
import ast, copy, importlib, io, json, logging, types, unittest
from types import SimpleNamespace as NS
from unittest.mock import MagicMock, patch
logging.disable(logging.CRITICAL)
import frappe
frappe.logger = lambda *a, **k: logging.getLogger('offline-review')
frappe.local.conf = frappe._dict()
frappe.local.session = frappe._dict(user='Synthetic Reviewer')
frappe.local.db = MagicMock()
from builder.ai.agent.registry import build_default_registry, ToolRegistry, Tool
from builder.ai.agent.loop import AgentRunner, CancelledError, render_page_context
from builder.ai.agent.tree import WorkingTree
from builder.ai import page_writer as pw, llm, codex
from builder.ai.prompts import Prompts
from builder.ai.session import AISession
from builder.ai.models import ModelRegistry
from builder.ai.agent.tools import data, query, conversation, memory
import tiktoken

def output(name, value):
    print(json.dumps({'probe': name, 'result': value}, ensure_ascii=False, default=str))

registry = build_default_registry()
schemas = registry.schemas()
encs = {n: tiktoken.get_encoding(n) for n in ['cl100k_base', 'o200k_base']}
def stats(s):
    return {'chars':len(s),'utf8_bytes':len(s.encode()),**{n:len(e.encode(s)) for n,e in encs.items()}}
serialize = lambda x: json.dumps(x, ensure_ascii=False, separators=(',', ':'))
totals = {'AGENT_SYSTEM':stats(Prompts.AGENT_SYSTEM), 'GENERATION_YAML':stats(Prompts.GENERATION_YAML), 'tools_compact_json':stats(serialize(schemas))}
for name in ['STYLING_RULES','MEMORY_RULES','VOICE','AI_TELLS']:
    totals[name] = stats(getattr(Prompts,name))
output('static_tokens',totals)
output('tools',sorted([{'name':s['function']['name'],**stats(serialize(s))} for s in schemas],key=lambda x:x['o200k_base'],reverse=True))
core={'read_block','query_blocks','update_block','update_blocks','add_block','remove_block','move_block','present_ui','preview_page'}
output('edit_subset_tokens', stats(serialize([s for s in schemas if s['function']['name'] in core])))

def runner(**kwargs):
    return AgentRunner('synthetic prompt', 'synthetic/model', 'synthetic-placeholder', user='Synthetic Reviewer', registry=registry, **kwargs)

def fake_row(role,content,status=''):
    return {'role':role,'content':content,'status':status,'metadata_json':''}
session = AISession(NS(name='synthetic-session'))
history = [fake_row('user','Original detailed brand identity')] + sum(([fake_row('assistant',f'answer {i}'),fake_row('user',f'follow-up {i}')] for i in range(1,7)),[])
with patch.object(frappe.db,'get_all',return_value=list(reversed(history))[:11]):
    context = session.build_context_messages()
output('history_window',{'available_rows':len(history),'returned_messages':len(context),'retains_original_brief':any('Original' in m['content'] for m in context),'first':context[0]})

# Invalid YAML can be salvaged into a blank root, then accepted for persistence.
for label,text in [('bare-root','el: div\nc:'),('broken-heading','el: div\nc:\n  - el: h1\n    text: unescaped: colon\n  - el: p\n    text: final paragraph'),('wrapped-repeater','page:\n  el: div\n  repeat:\n    data: products\n    items: [{title: A, live: true}]\n    item: {el: p, bind: {innerHTML: title}}'),('json-python-values','el: div\nrepeat:\n  data: products\n  items: [{title: A, live: true, optional: null}]\n  item: {el: p, bind: {innerHTML: title}}')]:
    blocks,script=pw.expand_page_yaml(text)
    info={'accepted':bool(blocks),'blocks':blocks,'data_script':script}
    if script:
        try:
            exec(script,{'data':frappe._dict()})
            info['script_exec']='ok'
        except Exception as e:
            info['script_exec']=f'{type(e).__name__}: {e}'
    output('yaml_'+label,info)

# Real stream assembly repairs a cut-off mutating call and returns it as executable.
r=runner()
r.emit=MagicMock()
r.is_cancelled=lambda:False
raw='{"block_id":"headline","inner_text":"Only half'
stream=[codex.chunk(tool_calls=[codex.tool_call_delta(0,'call_test','update_block',raw)]),codex.chunk(finish_reason='length')]
with patch.object(llm,'complete_with_tools',return_value=iter(stream)):
    operations,text,raw_calls=r.stream_tool_round([])
output('truncated_tool_call',{'finish_reasons':r.finish_reasons,'repaired':r.args_repaired,'operations':operations})

# A clean transport EOF without response.completed is accepted by the Codex path.
class FakeResponse:
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def iter_lines(self):
        yield b'data: {"type":"response.output_text.delta","item_id":"msg_a","delta":"Partial page"}'
        yield b''
with patch.object(codex,'open_stream',return_value=FakeResponse()):
    chunks=list(codex.stream_chunks('fake',{}))
output('codex_eof',{'chunks':len(chunks),'text':''.join(c.choices[0].delta.content or '' for c in chunks),'finish_reasons':[c.choices[0].finish_reason for c in chunks]})

# No central budget protects broad tool results; synthetic records only.
root={'blockId':'root','element':'div','children':[{'blockId':f'p{i}','element':'p','innerHTML':('Bespoke handmade ceramics for small daily rituals. ' * 90)} for i in range(100)]}
ctx=NS(page_root=lambda:root)
result=query.run_query_blocks(ctx,{'text_only':True})
output('query_blocks_100_paragraphs',stats(result))
meta=NS(fields=[NS(fieldname='script',fieldtype='Code')])
with patch.object(frappe.db,'exists',return_value=True), patch.object(frappe,'get_meta',return_value=meta),patch.object(frappe,'get_list',return_value=[{'name':str(i),'script':'body { color: red; }\n'*500} for i in range(100)]):
    result=data.query_records(NS(),{'doctype':'SyntheticCode','fields':['name','script'],'limit':100})
output('query_records_100_code_fields',stats(result))

# Document-level and field-level authorization are not checked by get_document.
doc=MagicMock()
doc.name='synthetic-owned-by-someone-else'
doc.as_dict.return_value={'name':doc.name,'restricted_field':'SYNTHETIC RESTRICTED VALUE'}
doc.check_permission.side_effect=frappe.PermissionError('Synthetic record access denied')
meta=NS(issingle=False,fields=[NS(fieldname='restricted_field',fieldtype='Data')])
with patch.object(frappe.db,'exists',return_value=True),patch.object(frappe,'has_permission',return_value=True),patch.object(frappe,'get_meta',return_value=meta),patch.object(frappe,'get_doc',return_value=doc):
    result=data.get_document(NS(),{'doctype':'SyntheticPrivateRecord','name':doc.name})
output('document_permission',{'returned_synthetic_restricted_value':'SYNTHETIC RESTRICTED VALUE' in result,'record_permission_checked':doc.check_permission.called,'field_permissions_applied':doc.apply_fieldlevel_read_permissions.called})

# Actual loop discards server tools following a successful terminal tool.
r=runner()
r.tree=WorkingTree({'blockId':'root','element':'div'})
r.build_messages=lambda:[{'role':'system','content':'test'},{'role':'user','content':'test'}]
r.emit=MagicMock();r.is_cancelled=lambda:False
reg=ToolRegistry()
terminal=MagicMock(return_value=None)
after=MagicMock(return_value='applied')
reg.extend([Tool('pause','terminal','',{},handler=terminal),Tool('later','server','',{},handler=after)])
r.registry=reg
ops=[{'tool_name':'pause','args':{}},{'tool_name':'later','args':{}}]
calls=[{'id':str(i),'function':{'name':o['tool_name'],'arguments':'{}'}} for i,o in enumerate(ops)]
r.call_tool_llm=lambda messages:(ops,'',calls)
with patch.object(ModelRegistry,'get_label',return_value='Fake'):
    r.run_turn(0)
output('terminal_drops_later_tool',{'terminal_executed':terminal.called,'later_executed':after.called,'usage_persisted':False})

# A rejected duplicate run clears an existing cancel before acquiring its lock.
r=runner(session_id='synthetic-session')
r.clear_cancel_flag=MagicMock();r.emit=MagicMock()
with patch.object(AISession,'start_run',return_value=None):
    r.run()
output('busy_worker_clears_cancel',{'cancel_cleared_before_rejection':r.clear_cancel_flag.call_count})

# Failed/cancelled turns omit accumulated usage, steps and the already-created revert snapshot.
r=runner(session_id='synthetic-session')
r.usage['prompt_tokens']=12345
r.revert_snapshot='synthetic-revert'
r.applied_operations=[{'tool_name':'update_block','args':{}}]
r.emit=MagicMock()
for fn,args in [(r.fail_turn,['Synthetic failure']),(r.emit_cancelled,[])]:
    with patch.object(AISession,'try_append_message') as append:
        fn(*args)
output('metadata_'+fn.__name__,append.call_args.kwargs.get('metadata'))

# Artifact generation uses a separate transcript and loses failed stream output.
from builder.ai.agent import artifact
from builder.ai.agent.tools import preview
r=runner(page_id='synthetic-page',session_id='synthetic-session')
r.prompt='EXACT CURRENT USER WORDING, including a distinctive business fact'
r.emit=MagicMock();r.is_cancelled=lambda:False
minimal_root={'blockId':'root','element':'div','children':[{'blockId':'p','element':'p','innerHTML':'Hello'}]}
with patch.object(AISession,'build_context_messages_from_id',return_value=[]),patch.object(ModelRegistry,'supports_vision',return_value=False),patch.object(artifact,'clear_stream_buffer'),patch.object(llm,'complete',return_value=iter([codex.chunk(content='el: div\nc: [{el: p, text: Hello}]'),codex.chunk(finish_reason='stop')])) as complete,patch.object(pw,'persist_page',return_value=(minimal_root,'')):
    artifact.generate_page_yaml(r,{'brief':'LOSSY BRIEF'})
    sent=complete.call_args.args[1]
output('generator_context',{'roles':[m['role'] for m in sent],'contains_current_prompt':r.prompt in serialize(sent),'contains_brief':'LOSSY BRIEF' in serialize(sent),'contains_saved_memory':'Saved memory' in serialize(sent)})

def broken_stream():
    yield codex.chunk(content='el: div\nc: [{el: p, text: Paid-for valid prefix}]')
    raise ConnectionError('Synthetic transport drop')
with patch.object(AISession,'build_context_messages_from_id',return_value=[]),patch.object(ModelRegistry,'supports_vision',return_value=False),patch.object(artifact,'clear_stream_buffer') as clear,patch.object(llm,'complete',return_value=broken_stream()),patch.object(pw,'persist_page') as persist:
    try:
        artifact.generate_page_yaml(r,{'brief':'Synthetic brief'})
    except Exception as exc:
        error=type(exc).__name__
output('generator_stream_failure',{'error':error,'partial_persisted':persist.called,'buffer_deleted':clear.called})

with patch('builder.html_preview_image.render',return_value=b'fake') as render:
    preview.render_page_image(NS(get_preview_html=lambda **k:'<section style="min-height:100vh">Hero</section>'))
output('preview_geometry',{'renderer_dimensions':render.call_args.kwargs,'100vh_height_px':render.call_args.kwargs['height'],'max_reviewed_pixels':preview.TILE_HEIGHT*preview.MAX_TILES})

# Boundary validity: a read-only call is accidentally classified as a mutation.
r=runner();r.emit=MagicMock();r.run_handler=lambda *a:'No images found';r.drain_queued_ops=lambda:[]
r.run_op({'tool_name':'search_images','args':{'query':'synthetic'}},{})
output('search_is_mutation',{'server_mutations':r.server_mutations})

# After the history window fills, cross-turn history prefix moves even without edits.
sys_prompt={'role':'system','content':'Static system'}
def prompt_from_history(rows):
    return [sys_prompt,*rows,{'role':'user','content':'Page context'},{'role':'assistant','content':'Understood. I have the current context.'},{'role':'user','content':'Current request'}]
rows=[{'role':'user' if i%2==0 else 'assistant','content':f'message {i}'} for i in range(12)]
a=prompt_from_history(rows[:10]);b=prompt_from_history(rows[2:12])
common=0
for x,y in zip(a,b):
    if x!=y:break
    common+=1
output('sliding_window_cache_prefix',{'common_messages':common,'shared_roles':[m['role'] for m in a[:common]]})

# Classify only static test functions, no source execution.
from pathlib import Path
files=list(Path('/home/t3run/builder/builder/ai').glob('test_*.py'))
methods=[]
for f in files:
    methods += [(str(f.name),node.name) for node in ast.walk(ast.parse(f.read_text())) if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith('test_')]
output('test_inventory',{'test_files':len(files),'test_methods':len(methods),'direct_run_turn_references':sum('run_turn(' in f.read_text() for f in files),'direct_stream_tool_round_references':sum('stream_tool_round(' in f.read_text() for f in files)})

# Compressed icons lose editing and interaction information, not just SVG bytes.
from builder.ai.block_codec import BlockCodec
icon={'blockId':'icon-edit-me','element':'svg','blockName':'Arrow','customAttributes':{'data-lucide':'arrow-right','id':'next'},'attributes':{'title':'Next'},'baseStyles':{'color':'red'},'mobileStyles':{'display':'none'},'classes':['motion-hook'],'innerHTML':'<svg />'}
output('icon_context_loss',BlockCodec.compress(icon))

# Switching a model on an established session is not saved for confirmation resume.
from builder.ai import api
class SyntheticSession:
    name='synthetic-session'
    def append_message(self,*args,**kwargs):return 'synthetic-message'
with patch.object(AISession,'is_session_running',return_value=False),patch.object(AISession,'get',return_value=SyntheticSession()),patch.object(ModelRegistry,'get_default',side_effect=lambda m:m),patch.object(ModelRegistry,'is_known_model',return_value=True),patch.object(api,'resolve_api_key',return_value='synthetic-placeholder'),patch.object(frappe,'enqueue') as enqueue,patch.object(frappe.db,'get_value',return_value=('synthetic-page','model-original')),patch.object(AISession,'latest_canvas_theme',return_value='light'):
    frappe.local.response=frappe._dict()
    # The decorator enforces the application's page-write permission; bypass it to test the function body.
    target=api.run
    while hasattr(target,'__wrapped__'):target=target.__wrapped__
    target('switching models','synthetic-page',model='model-selected-now',session_id='synthetic-session')
    first=enqueue.call_args.kwargs['model']
    api.resume_after_action('synthetic-session','Applied synthetic action')
    second=enqueue.call_args.kwargs['model']
output('confirmation_model_drift',{'explicit_turn_model':first,'resumed_model':second})

# Pure existing tests: replace FrappeTestCase only for reviewed, DB-free modules.
utils=types.ModuleType('frappe.tests.utils');utils.FrappeTestCase=unittest.TestCase
sys.modules['frappe.tests.utils']=utils
modules=['test_page_writer','test_tree_apply','test_codex','test_llm','test_cache_markers','test_selectors','test_lucide','test_artifact']
suite=unittest.TestSuite()
for name in modules:
    module=importlib.import_module('builder.ai.'+name)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
buffer=io.StringIO()
result=unittest.TextTestRunner(stream=buffer,verbosity=1).run(suite)
output('existing_offline_tests',{'modules':modules,'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'details':buffer.getvalue()})
