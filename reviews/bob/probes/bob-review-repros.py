"""Offline, source-extracted checks: no Frappe import, database, Redis, queue or model."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock
import time

ROOT = Path('/home/t3run/builder')

def functions(path, names, namespace):
    tree = ast.parse((ROOT / path).read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    for node in nodes:
        node.decorator_list = []
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(ROOT / path), 'exec'), namespace)

def methods(path, cls, names, namespace):
    tree = ast.parse((ROOT / path).read_text())
    source_class = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
    source_class.body = [n for n in source_class.body if isinstance(n, ast.FunctionDef) and n.name in names]
    source_class.bases = []
    source_class.decorator_list = []
    exec(compile(ast.Module(body=[source_class], type_ignores=[]), str(ROOT / path), 'exec'), namespace)
    return namespace[cls]

ns = {'time': time, 'logger': Mock(), 'AISession': NS(start_run=lambda _: 'token', end_run=Mock()), 'locks': Mock()}
Runner = methods('builder/ai/agent/loop.py', 'AgentRunner', ['run','emit_cancelled','fail_turn'], ns)
r = Runner(); r.session_id='S';r.page_id='P';r.model='M';r.user='U';r.held_locks=[];r.cancelled=True
r.clear_cancel_flag=lambda: setattr(r,'cancelled',False)
seen=[];r.run_turn=lambda _: seen.append(r.cancelled);r.run()
assert seen == [False]
print('REPRODUCED Worker clears an already-requested cancellation before starting work')
r.cancelled=True;ns['AISession'].start_run=lambda _:None;r.emit=Mock();r.run()
assert r.cancelled is False
print('REPRODUCED A rejected duplicate worker clears the running worker cancellation flag')
ns['AISession'].try_append_message=Mock();r.applied_operations=[{'tool_name':'update_block'}];r.revert_snapshot='snap';r.emit=Mock();r.emit_cancelled()
assert ns['AISession'].try_append_message.call_args.kwargs['metadata'] == {'status':'cancelled'}
print('REPRODUCED Cancel final message discards an existing revert snapshot pointer')
r.fail_turn('provider unavailable')
assert ns['AISession'].try_append_message.call_args.kwargs['metadata'] == {'status':'error'}
print('REPRODUCED Error final message discards an existing revert snapshot pointer')

records=[];queued=[]
class Session:
    name='S'
    def append_message(self, role, prompt, **kwargs): records.append((role,prompt))
session=Session()
frappe=NS(local=NS(response=NS()),session=NS(user='U'),enqueue=lambda *a,**kw:queued.append(kw))
api_ns={'frappe':frappe,'logger':Mock(),'_':lambda x:x,'AISession':NS(is_session_running=lambda s:False,get=lambda *a,**kw:session),'ModelRegistry':NS(get_default=lambda m:m,is_known_model=lambda m:True),'resolve_api_key':lambda m:'mock-key','run_agent_job':lambda:None}
functions('builder/ai/api.py',['run'],api_ns)
a=api_ns['run']('first','P',model='M',session_id='S');b=api_ns['run']('second','P',model='M',session_id='S')
assert a['status']==b['status']=='accepted' and len(queued)==len(records)==2
print('REPRODUCED Two submissions while jobs are queued both persist prompts and enqueue runs')

rows=[{'role':'assistant','content':'old'} , {'role':'user','content':'first'}, {'role':'user','content':'second'}]
ctxns={'frappe':NS(db=NS(get_all=lambda *a,**kw:list(reversed(rows))))}
SessionContext=methods('builder/ai/session.py','AISession',['build_context_messages'],ctxns)
s=SessionContext();s._doc=NS(name='S');s.MESSAGE_DOCTYPE='Builder AI Message';s.CONTEXT_WINDOW=10
context=s.build_context_messages()
assert [m['content'] for m in context] == ['old','first']
print('REPRODUCED First queued job replays its own prompt as history when a newer queued prompt exists')
print('6/6 source-extracted defect checks passed; mocks only')
