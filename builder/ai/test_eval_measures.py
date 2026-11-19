import json

from frappe.tests.utils import FrappeTestCase

from builder.ai.eval import ScenarioRun
from builder.ai.eval.measures import PageMeasure, card_measures, is_reflex, reply_measures
from builder.ai.eval.scenarios import Scenario

LABEL = {
	"element": "p",
	"innerHTML": "STUDIO HOURS",
	"baseStyles": {"textTransform": "uppercase", "fontSize": "11px"},
}


def section(*children, **styles) -> dict:
	return {"element": "section", "baseStyles": styles, "children": list(children)}


def page(*sections) -> dict:
	return {"element": "div", "baseStyles": {"backgroundColor": "#F4F0E8"}, "children": list(sections)}


class TestPageMeasures(FrappeTestCase):
	def test_counts_a_band_with_only_labels_or_nothing_as_empty(self):
		root = page(
			section(LABEL, backgroundColor="#23201C"),
			section(padding="64px 24px"),
			section(),
			section({"element": "p", "innerHTML": "Wheel throwing, four Saturdays"}),
			section({"element": "img", "attributes": {"src": "/files/kiln.jpg"}}),
			section({"element": "div", "isRepeaterBlock": True}),
		)

		self.assertEqual(PageMeasure(root).measures()["empty_sections"], 2)

	def test_a_reflex_face_counts_in_any_of_its_cuts(self):
		self.assertTrue(is_reflex("Cormorant Garamond"))
		self.assertTrue(is_reflex("IBM Plex Sans"))
		self.assertFalse(is_reflex("Bodoni Moda"))

	def test_counts_replies_that_narrate_the_turn(self):
		reply = "I tightened the layout; the latest preview couldn't be refreshed after a rejected edit."

		self.assertEqual(reply_measures(reply)["process_talk"], 2)


class TestCardMeasures(FrappeTestCase):
	def test_counts_colour_questions_and_tiles_on_the_stock_cream(self):
		ui = [
			{"kind": "color_input", "colors": [{"label": "Background", "value": "#F5F1E8"}]},
			{
				"kind": "choices",
				"options": [
					{"label": "The Practice Journal", "colors": ["#F4F0E7", "#233A32", "#C97855"]},
					{"label": "The Signal Board", "colors": ["#171916", "#C5E94C"]},
				],
			},
		]

		card = card_measures({"metadata_json": json.dumps({"ui": ui})})

		self.assertEqual((card["colour_steps"], card["stock_tiles"]), (1, 1))


class TestScenarioGates(FrappeTestCase):
	def broke(self, result: dict, **scenario) -> list[str]:
		run = ScenarioRun(Scenario("s", "p", **scenario), "m", None, "/tmp")
		return run.broke(result)

	def test_the_stock_look_fails_only_where_the_look_was_left_to_bob(self):
		result = {"page": {"cream_ground": 1, "reflex_faces": 0}}

		self.assertEqual(self.broke(result, fresh_look=True), ["stock_look"])
		self.assertEqual(self.broke(result), [])

	def test_a_colour_question_fails_any_scenario(self):
		result = {"card": None, "first_card": {"colour_steps": 1}}

		self.assertEqual(self.broke(result), ["colour_step"])
