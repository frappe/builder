"""Trace review scenarios to executable evidence without equating unit tests with design quality.

On a disposable site: bench --site SITE execute builder.ai.acceptance.run
Paid model/image transports are disabled in this deterministic runner.
"""

import fnmatch
import io
import itertools
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import frappe

DIRECTORY = Path(__file__).with_name("acceptance")


class EvidenceResult(unittest.TextTestResult):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.outcomes = {}

	def addSuccess(self, test):
		super().addSuccess(test)
		self.outcomes[test.id()] = "passed"

	def addFailure(self, test, err):
		super().addFailure(test, err)
		self.outcomes[test.id()] = "failed"

	def addError(self, test, err):
		super().addError(test, err)
		self.outcomes[test.id()] = "error"

	def addSkip(self, test, reason):
		super().addSkip(test, reason)
		self.outcomes[test.id()] = f"skipped: {reason}"


def scenarios():
	return json.loads((DIRECTORY / "scenarios.json").read_text())


def scenario_evidence(case, outcomes, browser):
	selected = {
		name: status
		for name, status in outcomes.items()
		if any(fnmatch.fnmatchcase(name, pattern) for pattern in case["tests"])
	}
	checks = [check for check in browser.get("checks", []) if case["id"] in check.get("scenarios", [])]
	unresolved = [
		pattern
		for pattern in case["tests"]
		if not any(fnmatch.fnmatchcase(name, pattern) for name in outcomes)
	]
	return {
		**case,
		"test_results": selected,
		"browser_checks": checks,
		"unresolved_test_patterns": unresolved,
		"status": "invariant_failed"
		if unresolved
		or any(status != "passed" for status in selected.values())
		or any(not check["passed"] for check in checks)
		else "partial_evidence"
		if selected or checks
		else "evaluation_required",
		"acceptance": "Requires the specified scenario experiment; passing a sub-invariant is not a whole-scenario pass.",
	}


def run(output_path=None, browser_path=None):
	frappe.only_for("System Manager")
	if not frappe.conf.get("allow_tests"):
		raise ValueError("Enable allow_tests on a disposable site before running acceptance fixtures")
	modules = [f"builder.ai.{file.stem}" for file in sorted(Path(__file__).parent.glob("test_*.py"))]
	log = io.StringIO()
	with (
		patch.dict(frappe.conf, {"builder_ai_runtime": "rq"}),
		patch("litellm.completion", side_effect=AssertionError("Live model calls are disabled")),
		patch("litellm.acompletion", side_effect=AssertionError("Live model calls are disabled")),
		patch("builder.ai.media.requests.post", side_effect=AssertionError("Live image calls are disabled")),
		patch("builder.ai.media.requests.get", side_effect=AssertionError("Live stock calls are disabled")),
	):
		suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
		result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=EvidenceResult).run(suite)
	browser = json.loads(Path(browser_path).read_text()) if browser_path else {}
	report = {
		"tests_run": result.testsRun,
		"regressions_passed": result.wasSuccessful(),
		"paid_calls": 0,
		"scenarios": [scenario_evidence(case, result.outcomes, browser) for case in scenarios()],
		"log": log.getvalue(),
	}
	if output_path:
		Path(output_path).write_text(json.dumps(report, indent=2, ensure_ascii=False))
	return report


def pairwise_plan():
	axes = {
		"page": ["new", "existing", "component", "project"],
		"session": ["new", "long", "question", "cancelled", "reconnect"],
		"viewport": ["desktop", "mobile", "rtl", "dark", "reduced_motion"],
		"asset": ["upload", "stock", "generated", "missing"],
		"provider": ["vision", "text", "failure", "missing_usage"],
		"editor": ["single", "two_tabs", "two_users", "permission_change"],
	}
	keys = list(axes)
	candidates = [
		(values, {(i, values[i], j, values[j]) for i in range(len(keys)) for j in range(i + 1, len(keys))})
		for values in itertools.product(*axes.values())
	]
	remaining = set().union(*(pairs for _, pairs in candidates))
	plan = []
	while remaining:
		values, covered = max(candidates, key=lambda item: len(item[1] & remaining))
		plan.append({"dimensions": dict(zip(keys, values, strict=True)), "status": "not_run"})
		remaining -= covered
	return plan
