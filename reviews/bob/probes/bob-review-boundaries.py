"""More isolated boundary probes; writes only scratch files under /tmp."""

import ast
import copy
import json
import logging
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe

frappe.logger = lambda *a, **k: logging.getLogger("bob-review-null")
logging.getLogger("bob-review-null").addHandler(logging.NullHandler())
logging.getLogger("bob-review-null").propagate = False
from builder.ai import page_writer as pw
from builder.ai.agent.tools import preview
from builder.ai.agent.tree import WorkingTree

ROOT = Path("/home/t3run/builder")


def method(path, cls, name, namespace):
	tree = ast.parse((ROOT / path).read_text())
	klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
	fn = copy.deepcopy(next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == name))
	fn.decorator_list = []
	# Offline audit executes fixed local-source fixtures without user input or a live site.
	exec(  # nosemgrep: frappe-codeinjection-eval
		compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), str(ROOT / path), "exec"),
		namespace,
	)
	return namespace[name]


results = {}
b = pw.convert_yaml_block({"el": "section", "attrs": {"id": "hero", "aria-label": "Hero"}})
t = WorkingTree(b)
msg = t.apply("update_block", {"block_id": b["blockId"], "attributes": {"id": None, "aria-label": None}})
results["generated_attributes_removal"] = {"message": msg, "remaining_attributes": b.get("attributes")}


class FakeDB:
	def __init__(self):
		self.points = set()
		self.commits = 0

	def savepoint(self, name):
		self.points.add(name)

	def commit(self):
		self.points.clear()
		self.commits += 1

	def rollback(self, save_point):
		if save_point not in self.points:
			raise RuntimeError("savepoint no longer exists")


db = FakeDB()
fakefrappe = SimpleNamespace(db=db, generate_hash=lambda **k: "fixturehash")
run_handler = method(
	"builder/ai/agent/loop.py",
	"AgentRunner",
	"run_handler",
	{
		"frappe": fakefrappe,
		"CancelledError": type("CancelledError", (Exception,), {}),
		"logger": logging.getLogger("bob-review-null"),
	},
)
with tempfile.TemporaryDirectory(prefix="bob-review-script-", dir="/tmp") as tmp:
	hook = method(
		"builder/builder/doctype/builder_client_script/builder_client_script.py",
		"BuilderClientScript",
		"update_script_file",
		{
			"frappe": fakefrappe,
			"os": os,
			"get_files_path": lambda p: os.path.join(tmp, p),
			"jsmin": lambda s, **k: s,
			"compress": lambda s: s,
		},
	)

	def db_set(*args, **kwargs):
		if kwargs.get("commit"):
			db.commit()

	doc = SimpleNamespace(
		script_type="JavaScript",
		script="void 0;",
		name="fixture",
		get_file_name_from_url=lambda: None,
		db_set=db_set,
	)

	def handler(ctx, args):
		hook(doc)
		raise ValueError("simulated attach failure after file save")

	try:
		outcome = run_handler(
			SimpleNamespace(server_mutations=0),
			SimpleNamespace(handler=handler),
			{"tool_name": "set_page_script", "args": {}},
		)
	except Exception as e:
		outcome = f"{type(e).__name__}: {e}"
	results["script_savepoint"] = {
		"commits": db.commits,
		"outcome": outcome,
		"file_survives_failed_tool": any(Path(tmp).rglob("*.js")),
	}

with (
	patch.object(frappe, "db", SimpleNamespace(exists=lambda *a: True)),
	patch.object(frappe, "get_doc", return_value=SimpleNamespace(name="fixture")),
	patch.object(preview, "render_page_image", side_effect=RuntimeError("Jinja/template failure fixture")),
):
	result = preview.run_preview_page(SimpleNamespace(page_id="fixture", preview_count=0), {})
results["preview_masks_template_error"] = result
Path("/tmp/bob-review-boundaries.json").write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
