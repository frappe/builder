"""Read-only Bob probes: real pure code; all site/database access mocked."""

import ast
import copy
import io
import json
import logging
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe

frappe.logger = lambda *a, **k: logging.getLogger("bob-review-null")
logging.getLogger("bob-review-null").addHandler(logging.NullHandler())
logging.getLogger("bob-review-null").propagate = False
from builder.ai import page_writer as pw
from builder.ai.agent.pending import build_form_script
from builder.ai.agent.tools import data
from builder.ai.agent.tree import WorkingTree
from builder.ai.block_codec import BlockCodec

ROOT = Path("/home/t3run/builder")
results = {}


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


# Existing tests that really are pure: exclude the two that now resolve components via DB.
suite = unittest.defaultTestLoader.loadTestsFromNames(
	["builder.ai.test_tree_apply", "builder.ai.test_page_writer"]
)


def flatten(s):
	for t in s:
		if isinstance(t, unittest.TestSuite):
			yield from flatten(t)
		else:
			yield t


skip = {"test_add_converts_yaml_vocab", "test_component_reference_and_attrs"}
stream = io.StringIO()
res = unittest.TextTestRunner(stream=stream, verbosity=1).run(
	unittest.TestSuite(t for t in flatten(suite) if t._testMethodName not in skip)
)
results["existing_pure_tests"] = {
	"run": res.testsRun,
	"failures": len(res.failures),
	"errors": len(res.errors),
	"excluded_db_dependent": sorted(skip),
	"output": stream.getvalue(),
}

# Run the actual apply_client_ops method without constructing a runner/model/site.
tree = WorkingTree(
	{
		"blockId": "root",
		"element": "div",
		"children": [{"blockId": "title", "element": "h1", "innerHTML": "old"}],
	}
)
op = {
	"tool_name": "update_blocks",
	"args": {"patches": [{"block_id": "title", "inner_text": "{{ missing.title }}"}]},
}
ctx = SimpleNamespace(
	tree=tree,
	page_id=None,
	applied_operations=[],
	tool_failures=[],
	ensure_revert_snapshot=lambda: None,
	emit=Mock(),
)
apply = method(
	"builder/ai/agent/loop.py",
	"AgentRunner",
	"apply_client_ops",
	{"SNAPSHOT_TOOLS": set(), "logger": logging.getLogger("bob-review-null")},
)
verdicts, accepted = apply(ctx, [op])
assert tree.resolve("title")["innerHTML"] == "old" and accepted == [op]
results["rejected_bulk_forwarded"] = {
	"result": verdicts[id(op)],
	"forwarded_patches": accepted[0]["args"]["patches"],
	"tool_failures": ctx.tool_failures,
}
Path("/tmp/bob-review-rejected-op.json").write_text(json.dumps(op))

results["remove_root"] = {
	"message": tree.apply("remove_block", {"block_id": "root"}),
	"root_survives": tree.root is not None,
}
results["forbidden_element"] = {
	"message": tree.apply("update_block", {"block_id": "title", "element": "script"}),
	"server_element": tree.resolve("title")["element"],
}

styled = WorkingTree({"blockId": "root", "element": "div", "mobileStyles": {"display": "none"}})
results["cannot_clear_style"] = {
	"message": styled.apply("update_block", {"block_id": "root", "mobile_styles": {"display": None}}),
	"remaining": styled.root["mobileStyles"],
}

node = {
	"el": "section",
	"c": [{"el": "div", "repeat": {"data": "cards", "item": {"el": "p", "bind": {"innerHTML": "title"}}}}],
}
original = pw.convert_yaml_block(node)
roundtrip = pw.convert_yaml_block(BlockCodec.compress(original))
results["repeater_roundtrip"] = {
	"before": original["children"][0].get("isRepeaterBlock"),
	"after": roundtrip["children"][0].get("isRepeaterBlock"),
	"read_shape": BlockCodec.compress(original)["c"][0]["repeat"],
}
icon = pw.convert_icon_block(
	{
		"icon": "star",
		"attrs": {"aria-label": "Favorite"},
		"classes": ["favorite"],
		"m_style": {"display": "none"},
		"stroke": 4,
	}
)
results["icon_compression"] = {
	"has_ref": "ref" in BlockCodec.compress(icon),
	"has_attrs": "attrs" in BlockCodec.compress(icon),
	"has_mobile": "m_style" in BlockCodec.compress(icon),
	"has_classes": "classes" in BlockCodec.compress(icon),
}
results["blockcodec_ref_loss"] = BlockCodec.expand(
	BlockCodec.compress({"blockId": "stable", "element": "p"})
).get("blockId")
results["generated_component_fields"] = pw.convert_yaml_block(
	{"el": "div", "props": {"title": "Hi"}, "client_script": {"js": "void 0"}, "componentVersion": "v1"}
)

for name, fixture in {
	"boolean_null": {
		"el": "div",
		"repeat": {"data": "cards", "items": [{"enabled": True, "title": None}], "item": {"el": "p"}},
	},
	"prefixed_data": {
		"el": "div",
		"repeat": {"data": "data.cards", "items": [{"title": "A"}], "item": {"el": "p"}},
	},
	"wrapped_root": {
		"page": {"el": "div", "repeat": {"data": "cards", "items": [{"title": "A"}], "item": {"el": "p"}}}
	},
}.items():
	script = pw.build_repeater_data_script(fixture)
	output = frappe._dict()
	try:
		# Offline audit executes fixed local-source fixtures without user input or a live site.
		exec(  # nosemgrep: frappe-codeinjection-eval
			script, {"data": output}
		)
		status = "ok"
	except Exception as e:
		status = type(e).__name__ + ": " + str(e)
	results["repeater_" + name] = {"script": script, "execution": status, "data_keys": list(output)}

# No network or writes: fake the database and a record with a deny-on-document check.
record = SimpleNamespace(
	name="fixture",
	as_dict=lambda: {"name": "fixture", "restricted_field": "FAKE-RESTRICTED-FIXTURE"},
	check_permission=Mock(side_effect=PermissionError()),
	apply_fieldlevel_read_permissions=Mock(),
)
meta = SimpleNamespace(issingle=False, fields=[])
with (
	patch.object(frappe, "db", SimpleNamespace(exists=lambda *a, **k: True)),
	patch.object(frappe, "has_permission", return_value=True),
	patch.object(frappe, "get_meta", return_value=meta),
	patch.object(frappe, "get_doc", return_value=record),
	patch.object(frappe, "as_json", side_effect=json.dumps),
):
	out = data.get_document(None, {"doctype": "Fixture", "name": "fixture"})
results["get_document_permission"] = {
	"returned_fixture_field": "FAKE-RESTRICTED-FIXTURE" in out,
	"doc_permission_checks": record.check_permission.call_count,
	"field_permission_checks": record.apply_fieldlevel_read_permissions.call_count,
}

with (
	patch.object(frappe, "db", SimpleNamespace(set_value=Mock())),
	patch.object(data, "missing_names", return_value=[]),
):
	scripts = {
		"write_alias": "doc = frappe.get_doc('Builder Page', 'fixture')\ndoc.page_title = 'Changed'\nsave = doc.save\nsave()",
		"email": "frappe.sendmail(recipients=['fixture@example.invalid'], subject='fixture', message='fixture')",
		"runtime_error": "data.cards = missing_name",
	}
	results["data_script_gate"] = {
		name: data.write_page_data_script(SimpleNamespace(page_id="fixture"), {"script": script})
		for name, script in scripts.items()
	}

Path("/tmp/bob-review-form.js").write_text(
	build_form_script("#contact", "fixture-submissions", ["email", "name_field", "consent", "plan"])
)
Path("/tmp/bob-review-probes.json").write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
