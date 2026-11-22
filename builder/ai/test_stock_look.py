import frappe
from frappe.tests.utils import FrappeTestCase

from builder.ai.agent.tools.conversation import run_present_ui
from builder.ai.agent.tools.settings import set_design_token
from builder.ai.session import AISession
from builder.ai.skills import Skills
from builder.ai.stock_look import REFLEX_FACES, TIRED_FACES, FontDraw, is_cream


class Ctx:
	def __init__(self):
		self.stock_grounds = set()


class TestCreamGround(FrappeTestCase):
	def test_tells_the_stock_cream_from_other_light_grounds(self):
		for cream in ("#F4F0E8", "#F1E9DB", "#F3F0E6", "#f5efe6", "#E9D8C1"):
			self.assertTrue(is_cream(cream), cream)
		for other in ("#FFFFFF", "#F8F8F6", "#F2F4F7", "#263B35", "#B97857", "#D9C8AF", "#FAD7A0", "x"):
			self.assertFalse(is_cream(other), other)

	def test_a_cream_token_is_turned_back_once_then_saved(self):
		ctx = Ctx()
		args = {"token_name": "Kiln Chalk", "id": "test-kiln-chalk", "value": "#F4F0E8", "type": "Color"}

		first = set_design_token(ctx, args)
		self.assertTrue(first.startswith("FAILED: #F4F0E8 is a warm near-white"), first)
		self.assertFalse(frappe.db.exists("Builder Token", "test-kiln-chalk"))

		self.assertIn("var(--test-kiln-chalk)", set_design_token(ctx, args))
		self.assertEqual(frappe.db.get_value("Builder Token", "test-kiln-chalk", "value"), "#F4F0E8")

	def test_other_colours_save_at_once(self):
		out = set_design_token(
			Ctx(), {"token_name": "Test Kiln Ink", "id": "test-kiln-ink", "value": "#23201C"}
		)

		self.assertIn("var(--test-kiln-ink)", out)


class CardCtx(Ctx):
	def __init__(self):
		super().__init__()
		self.session_id = AISession.create({"page": None})._doc.name
		self.web_sources = []

	def timeline(self):
		return []

	def emit(self, *args, **kwargs):
		pass


class TestCreamTiles(FrappeTestCase):
	def test_a_card_with_a_cream_tile_is_turned_back_once_then_shown(self):
		ctx = CardCtx()
		options = [
			{"label": "The Kiln Ledger", "colors": ["#F4EEE2", "#272B25", "#C64C2F"]},
			{"label": "Glaze Atlas", "colors": ["#DCE5E1", "#283C3A"]},
		]
		args = {"text": "Which direction?", "ui": [{"kind": "choices", "options": options}]}

		first = run_present_ui(ctx, args)

		self.assertTrue(first.startswith("FAILED: #F4EEE2 on the direction tiles"), first)
		self.assertIsNone(run_present_ui(ctx, args))


class TestFontDraw(FrappeTestCase):
	def test_a_chat_draws_the_same_faces_every_turn(self):
		first, again, other = (
			FontDraw("chat-a").sample(),
			FontDraw("chat-a").sample(),
			FontDraw("chat-b").sample(),
		)

		self.assertEqual(len(first), 16)
		self.assertEqual(first, again)
		self.assertNotEqual(first, other)

	def test_never_draws_a_reflex_tired_or_popular_face(self):
		popular = {"Roboto", "Open Sans", "Lato", "Montserrat", "Poppins", "Inter", "Playfair Display"}
		for seed in range(20):
			for face in FontDraw(str(seed)).sample():
				self.assertFalse(face.startswith(REFLEX_FACES + TIRED_FACES), face)
				self.assertNotIn(face, popular)

	def test_the_new_page_skill_carries_the_chats_draw_and_the_stock_faces(self):
		guide = Skills.read("new-page", "chat-a")

		self.assertIn(", ".join(FontDraw("chat-a").sample()), guide)
		self.assertIn("in any of their cuts: Fraunces, Instrument Serif", guide)
		self.assertNotIn("{{", guide)
