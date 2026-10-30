"""Bob's prompt eval: fixed scenarios through the real agent loop, scored without a
judge model, so a prompt change is measured before it ships.

	bench --site builder.test execute builder.ai.eval.run \\
		--kwargs "{'model': 'codex/gpt-6-luna', 'fixture': 'page-94873e7a', 'label': 'develop'}"
	bench --site builder.test execute builder.ai.eval.compare --kwargs "{'a': '<dir>', 'b': '<dir>'}"

Each scenario runs on a scratch page (empty, or a copy of `fixture`, a designed page)
and everything the turn minted is deleted after, so scenarios don't leak into each
other. One run per scenario is a smoke test: pass repeat=3 before calling a close result.
"""

import json
import os
from collections import Counter
from dataclasses import dataclass
from statistics import median

import frappe

from .measures import (
	PageMeasure,
	authored_text,
	card_measures,
	read_json,
	reply_measures,
	run_measures,
	summary_line,
	write_json,
)


@dataclass
class Scenario:
	name: str
	prompt: str
	on_fixture: bool = False
	# at least one of these tools must run, and none of `forbid`
	expect_any: tuple = ()
	forbid: tuple = ()


EDITS = ("update_block", "update_blocks", "add_block", "remove_block", "move_block")

SCENARIOS = (
	Scenario(
		"bare-build", "Make a page for my yoga studio.", expect_any=("present_ui",), forbid=("generate_page",)
	),
	Scenario(
		"brief-build",
		"Build the landing page for Kiln & Clay, a pottery studio in Bandra, Mumbai, run by Meera Iyer "
		"since 2019. Sections: a hero; the classes (Wheel throwing, four Saturdays, ₹2,800; Hand building, "
		"₹2,200; Kids clay club, ₹1,500); open studio hours (Tuesday to Sunday, 10am to 8pm); the glaze "
		"wall where students pick their finishes; and a visit section with the address, 14 Chapel Road, "
		"Bandra West. Earthy terracotta and cream palette, editorial feel. Give it a look of its own, "
		"don't copy the site's other pages. Pick the photos yourself and build it now.",
		expect_any=("generate_page",),
	),
	Scenario(
		"edit",
		"Make the hero headline shorter and punchier, and give the main hero button our accent colour.",
		on_fixture=True,
		expect_any=EDITS,
		forbid=("generate_page",),
	),
	Scenario(
		"translate",
		"Translate all the text on this page into Hindi.",
		on_fixture=True,
		expect_any=("update_blocks",),
		forbid=("generate_page",),
	),
	Scenario(
		"redesign",
		"Redesign this whole page with a completely new look.",
		on_fixture=True,
		expect_any=("present_ui", "generate_page"),
	),
	Scenario(
		"opinion",
		"Should I use Comic Sans for the headings?",
		on_fixture=True,
		forbid=("generate_page", *EDITS),
	),
)

# What a turn can mint site-wide; anything created during a scenario is deleted after it.
MINTED = ("Builder Page", "Builder Component", "Builder Client Script", "Builder Token", "Builder AI Memory")


def run(model: str, fixture: str | None = None, label: str = "run", only=None, repeat: int = 1, out_dir=None):
	"""Run every scenario (or those named in `only`) `repeat` times, writing one JSON
	per attempt plus summary.json into `out_dir`. Returns the directory."""
	stamp = frappe.utils.now_datetime().strftime("%Y%m%d-%H%M")
	out_dir = out_dir or frappe.get_site_path("private", "bob-eval", f"{label}-{stamp}")
	os.makedirs(out_dir, exist_ok=True)
	results = []
	for scenario in SCENARIOS:
		if (only and scenario.name not in only) or (scenario.on_fixture and not fixture):
			continue
		for attempt in range(1, repeat + 1):
			result = ScenarioRun(scenario, model, fixture, out_dir, attempt).execute()
			results.append(result)
			write_json(os.path.join(out_dir, f"{scenario.name}-{attempt}.json"), result)
			print(summary_line(result))
	summary_path = os.path.join(out_dir, "summary.json")
	# a rerun of some scenarios replaces just those in an earlier run's summary
	if os.path.exists(summary_path):
		ran = {r["scenario"] for r in results}
		results = [r for r in read_json(summary_path)["results"] if r["scenario"] not in ran] + results
	write_json(summary_path, {"model": model, "label": label, "results": results})
	return out_dir


def compare(a: str, b: str):
	"""Two runs side by side: per scenario, the pass count, median prompt tokens and
	rounds, how often each tool ran, and the median of each page measure."""
	arms = [(os.path.basename(d.rstrip("/")), by_scenario(d)) for d in (a, b)]
	for name in sorted(arms[0][1].keys() | arms[1][1].keys()):
		print(f"\n## {name}")
		for label, scenarios in arms:
			if results := scenarios.get(name):
				print(f"  {label}: {arm_line(results)}")


def by_scenario(out_dir: str) -> dict[str, list[dict]]:
	scenarios: dict[str, list[dict]] = {}
	for result in read_json(os.path.join(out_dir, "summary.json"))["results"]:
		scenarios.setdefault(result["scenario"], []).append(result)
	return scenarios


def arm_line(results: list[dict]) -> str:
	scored = [r for r in results if "run" in r]
	line = f"{sum(r['ok'] for r in results)}/{len(results)} pass"
	if not scored:
		return line
	line += f" | prompt {median([r['run']['prompt_tokens'] or 0 for r in scored])}"
	line += f" | rounds {median([r['run']['rounds'] for r in scored])}"
	tools = Counter(tool for r in scored for tool in r["tools"])
	line += " | " + ", ".join(f"{tool} {n}" for tool, n in tools.most_common())
	if pages := [r["page"] for r in scored if r.get("page")]:
		line += " | " + " ".join(f"{k}={median([p[k] for p in pages])}" for k in pages[0])
	return line + f" | reply dashes {sum(r['reply']['dashes'] for r in scored)}"


class ScenarioRun:
	def __init__(self, scenario: Scenario, model: str, fixture: str | None, out_dir: str, attempt: int = 1):
		self.scenario = scenario
		self.attempt = attempt
		self.model = model
		self.fixture = fixture
		self.out_dir = out_dir

	def execute(self) -> dict:
		started = frappe.utils.now_datetime()
		page = self.make_page()
		try:
			return self.score(self.run_turn(page), page)
		except Exception as e:
			frappe.log_error(f"Bob eval: {self.scenario.name}")
			return {
				"scenario": self.scenario.name,
				"attempt": self.attempt,
				"ok": False,
				"error": repr(e)[:500],
			}
		finally:
			self.clean_up(started)

	def make_page(self):
		blocks = None
		if self.scenario.on_fixture:
			source = frappe.db.get_value(
				"Builder Page", self.fixture, ["draft_blocks", "blocks"], as_dict=True
			)
			blocks = source.draft_blocks or source.blocks
		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": f"Bob eval: {self.scenario.name}",
				"draft_blocks": blocks,
			}
		).insert(ignore_permissions=True)
		frappe.db.commit()
		return page

	def run_turn(self, page):
		from builder.ai import llm
		from builder.ai.agent.loop import AgentRunner
		from builder.ai.session import AISession

		session = AISession.create({"page": page.name}, self.model)
		session.append_message("user", self.scenario.prompt, message_type="chat", task_type="agent")
		frappe.db.commit()
		runner = AgentRunner(
			self.scenario.prompt,
			self.model,
			llm.resolve_api_key(self.model),
			page_id=page.name,
			session_id=session.name,
		)
		runner.run()
		frappe.db.commit()
		return runner

	def score(self, runner, page) -> dict:
		tools = [tool["name"] for step in runner.trace for tool in step.get("tools") or []]
		ran = set(tools)
		expected = not self.scenario.expect_any or bool(ran & set(self.scenario.expect_any))
		forbidden = sorted(ran & set(self.scenario.forbid))
		reply = self.final_reply(runner.session_id)
		result = {
			"scenario": self.scenario.name,
			"attempt": self.attempt,
			"ok": expected and not forbidden,
			"missing": [] if expected else list(self.scenario.expect_any),
			"forbidden": forbidden,
			"tools": list(dict.fromkeys(tools)),
			# each call's arguments, cut short: enough to read a brief or a card
			"calls": [
				[t["name"], str(t.get("args"))[:4000]]
				for step in runner.trace
				for t in step.get("tools") or []
			],
			"tool_calls": len(tools),
			"run": run_measures(runner),
			"reply": reply_measures(authored_text(reply)),
			"card": card_measures(reply) if reply.get("message_type") == "clarification" else None,
		}
		if ran & {"generate_page", *EDITS}:
			root = json.loads(frappe.db.get_value("Builder Page", page.name, "draft_blocks") or "[{}]")[0]
			result["page"] = PageMeasure(root).measures()
			result["screenshot"] = self.screenshot(page.name)
		return result

	def final_reply(self, session_id: str) -> dict:
		rows = frappe.get_all(
			"Builder AI Message",
			{"session": session_id, "role": "assistant"},
			["content", "message_type", "metadata_json"],
			order_by="creation desc",
			limit=1,
		)
		return rows[0] if rows else {}

	def screenshot(self, page_id: str) -> str | None:
		from builder.ai.agent.tools.preview import render_page_image

		try:
			image = render_page_image(frappe.get_doc("Builder Page", page_id))
		except Exception:
			return None
		path = os.path.join(self.out_dir, f"{self.scenario.name}-{self.attempt}.webp")
		with open(path, "wb") as f:  # nosemgrep
			f.write(image)
		return path

	def clean_up(self, since):
		frappe.db.rollback()
		for doctype in MINTED:
			for name in frappe.get_all(doctype, {"creation": [">=", since]}, pluck="name"):
				frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
		frappe.db.commit()
