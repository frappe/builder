import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from PIL import Image

from builder.ai import evaluation
from builder.ai.artifacts import Artifact
from builder.ai.session import AISession


class TestEvaluationEvidence(FrappeTestCase):
	def fixture(self, implementation):
		page = frappe.get_doc(
			{"doctype": "Builder Page", "page_title": "Evaluation evidence fixture"}
		).insert()
		session = AISession.create({"page": page.name})
		Artifact.save(
			page.name,
			"evaluation",
			{
				"case": evaluation.corpus()[1],
				"model": "private/model",
				"implementation": implementation,
				"sample": 1,
				"session": session.name,
			},
			identity="experiment",
		)
		return page.name

	def test_blind_pack_excludes_identity_and_rejects_stale_ratings(self):
		buffer = io.BytesIO()
		Image.new("RGB", (8, 8), "white").save(buffer, "WEBP")
		with (
			patch.dict(frappe.conf, {"allow_tests": True}),
			patch("builder.html_preview_image.render_full_page", return_value=buffer.getvalue()) as render,
		):
			pages = [self.fixture("baseline-private"), self.fixture("candidate-private")]
			for page in pages:
				captured = evaluation.capture(page)
				self.assertEqual(captured["runs"], [])
				self.assertEqual(set(captured["previews"]), {"desktop"})
			self.assertEqual(render.call_count, 2)
			with tempfile.TemporaryDirectory() as directory:
				result = evaluation.blind_pack(pages, str(Path(directory) / "review"))
				markup = Path(result["review"]).read_text()
				self.assertNotIn("mobile.webp", markup)
				self.assertEqual(len(list(Path(directory, "review").glob("*.webp"))), 2)
				self.assertNotIn("private/model", markup)
				self.assertNotIn("baseline-private", markup)
				self.assertIn("Candidate A", markup)
				identity = json.loads(Path(result["private_identity_key"]).read_text())
				self.assertEqual({row["page"] for row in identity.values()}, set(pages))
			ratings = dict.fromkeys(evaluation.RUBRIC, 3)
			value = evaluation.rate(pages[0], ratings, False, 2, "The interaction still needs a correction")
			self.assertFalse(value["accepted"])
			frappe.db.set_value("Builder Page", pages[0], "page_title", "Changed after capture")
			with self.assertRaisesRegex(ValueError, "Capture the current"):
				evaluation.rate(pages[0], ratings, True, 2, "Stale opinion")
