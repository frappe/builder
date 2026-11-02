"""Opt-in live experiments and blind review packs. Never part of the regression runner.

Call start explicitly on a disposable allow_tests site to incur one live model turn.
Continue questions/refinements in the returned editor chat, then capture and rate.
"""

import html
import json
import random
from pathlib import Path

import frappe

from builder.ai.artifacts import Artifact
from builder.ai.revisions import page_revision

RUBRIC = ("brief_fit", "factual_fidelity", "specificity", "hierarchy", "responsive_use", "interaction_use")


def require_evaluation_site():
	frappe.only_for("System Manager")
	if not frappe.conf.get("allow_tests"):
		raise ValueError("Use a disposable site with allow_tests enabled")


def corpus():
	return json.loads(Path(__file__).with_name("acceptance").joinpath("corpus.json").read_text())


def start(case_id: str, model: str, implementation: str, sample: int = 1):
	"""Start exactly one paid-capable turn; no automatic confirmations or synthetic user replies."""
	from builder.ai.api import run

	require_evaluation_site()
	case = next((item for item in corpus() if item["id"] == case_id), None)
	if not case or not implementation or not 1 <= int(sample) <= 10:
		raise ValueError("Choose a corpus case, implementation commit/label and sample 1–10")
	page = frappe.get_doc({"doctype": "Builder Page", "page_title": f"Bob evaluation: {case_id}"}).insert()
	artifact = Artifact.save(
		page.name,
		"evaluation",
		{"case": case, "implementation": implementation, "sample": int(sample), "model": model},
		identity="experiment",
	)
	accepted = run(case["prompt"], page.name, model=model, request_id=frappe.generate_hash(length=32))
	value = json.loads(artifact.payload_json)
	value["session"] = accepted["session_id"]
	artifact.payload_json = json.dumps(value)
	artifact.save(ignore_permissions=True)
	return {
		**accepted,
		"page": page.name,
		"editor": f"/builder/page/{page.name}",
		"expected": case["expected"],
	}


def experiment(page_id):
	return Artifact.get(Artifact.key(page_id, "evaluation", "experiment"), page_id, "evaluation")


def capture(page_id: str):
	from builder.ai.media import save_raster
	from builder.html_preview_image import render_full_page

	require_evaluation_site()
	doc, value = experiment(page_id)
	runs = frappe.get_all(
		"Builder AI Run",
		filters={"session": value["session"]},
		fields=["name", "model", "status", "creation", "finished_on", "metadata_json"],
		order_by="creation",
	)
	if any(row.status in ("queued", "running") for row in runs):
		raise ValueError("Wait for this experiment's active turn to finish")
	page = frappe.get_doc("Builder Page", page_id)
	revision = page_revision(page_id)
	image = render_full_page(page.get_preview_html(), width=1280, height=900, max_height=1800)
	previews = {"desktop": save_raster(page_id, image, f"evaluation-{page_id}-desktop", private=True)["url"]}
	for row in runs:
		row["metadata"] = json.loads(row.pop("metadata_json") or "{}")
	if page_revision(page_id) != revision:
		raise ValueError("The page changed during capture; capture the new revision")
	value.update(
		{
			"revision": revision,
			"previews": previews,
			"runs": runs,
			"captured_on": str(frappe.utils.now_datetime()),
			"coverage": "First 1800px; verify full-page interactions separately",
		}
	)
	doc.payload_json = json.dumps(value, default=str)
	doc.save(ignore_permissions=True)
	return value


def rate(page_id: str, ratings: dict, accepted: bool, corrections: int, notes: str):
	"""Human outcome; a completed turn is never inferred to be an accepted page."""
	require_evaluation_site()
	doc, value = experiment(page_id)
	if (
		not isinstance(ratings, dict)
		or set(ratings) != set(RUBRIC)
		or any(type(score) is not int or not 1 <= score <= 5 for score in ratings.values())
	):
		raise ValueError("Rate each rubric dimension from 1 to 5")
	if type(accepted) is not bool or type(corrections) is not int or corrections < 0 or not notes:
		raise ValueError("Record explicit acceptance, a nonnegative correction count and review notes")
	if value.get("revision") != page_revision(page_id):
		raise ValueError("Capture the current page before rating it")
	value.setdefault("reviews", []).append(
		{
			"reviewer": frappe.session.user,
			"ratings": ratings,
			"accepted": accepted,
			"corrections": corrections,
			"notes": notes[:4000],
			"revision": value["revision"],
		}
	)
	doc.payload_json = json.dumps(value)
	doc.save(ignore_permissions=True)
	return value["reviews"][-1]


def blind_pack(page_ids: list, output_directory: str, seed: int = 0):
	"""Export captured images without model/implementation labels; keep identity.json from reviewers."""
	require_evaluation_site()
	if not isinstance(page_ids, list) or not 2 <= len(page_ids) <= 20 or len(set(page_ids)) != len(page_ids):
		raise ValueError("Compare 2–20 distinct captured pages")
	values = [(page, experiment(page)[1]) for page in page_ids]
	if len({value["case"]["id"] for _, value in values}) != 1:
		raise ValueError("Blind comparisons must use the same corpus case")
	if any(
		not value.get("previews", {}).get("desktop") or value.get("revision") != page_revision(page)
		for page, value in values
	):
		raise ValueError("Capture each current page before exporting")
	root = Path(output_directory)
	root.mkdir(parents=True, exist_ok=False)
	random.Random(seed).shuffle(values)
	identity, cards = {}, []
	for index, (page, value) in enumerate(values):
		label = chr(65 + index)
		identity[label] = {
			"page": page,
			"model": value["model"],
			"implementation": value["implementation"],
			"sample": value["sample"],
		}
		file = frappe.get_doc("File", {"file_url": value["previews"]["desktop"]})
		file.check_permission("read")
		(root / f"{label}-desktop.webp").write_bytes(file.get_content())
		cards.append(
			f'<article><h2>Candidate {label}</h2><img src="{label}-desktop.webp" alt="Desktop"></article>'
		)
	case = values[0][1]["case"]
	markup = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Blind Bob comparison</title><style>body{font:16px system-ui;margin:24px;color:#222}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px}img{max-width:100%;vertical-align:top}article{border:1px solid #ccc;padding:12px}</style>'
	markup += f"<h1>{html.escape(case['id'])}</h1><p>{html.escape(case['prompt'])}</p><p>Score each dimension 1–5: {html.escape(', '.join(RUBRIC))}. Record corrections and acceptance separately. Screenshots cover the first 1800 pixels; test full pages separately.</p><main>{''.join(cards)}</main></html>"
	(root / "index.html").write_text(markup)
	(root / "identity.json").write_text(json.dumps(identity, indent=2))
	return {
		"review": str(root / "index.html"),
		"private_identity_key": str(root / "identity.json"),
		"seed": seed,
	}
