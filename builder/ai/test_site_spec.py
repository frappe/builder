"""Unit tests for the SiteSpec parser/validator (builder/ai/site_spec.py).

The architect's JSON is LLM-produced, so these pin the defensive coercion:
route normalization, dedupe, page cap, and rejection of empty specs.
"""

import unittest

from builder.ai import site_spec as ss


class TestNormalizeRoute(unittest.TestCase):
	def test_variants(self):
		self.assertEqual(ss.normalize_route("About Us"), "/about-us")
		self.assertEqual(ss.normalize_route("/Contact/"), "/contact")
		self.assertEqual(ss.normalize_route("//a//b//"), "/a/b")
		self.assertEqual(ss.normalize_route("/"), "/")
		self.assertEqual(ss.normalize_route(""), "")
		self.assertEqual(ss.normalize_route(None), "")


class TestThemeVariable(unittest.TestCase):
	def test_strips_leading_dashes_and_defaults_type(self):
		v = ss.ThemeVariable.from_dict({"variable_name": "--brand-primary", "value": "#0af"})
		self.assertEqual(v.variable_name, "brand-primary")
		self.assertEqual(v.type, "Color")
		self.assertEqual(v.group, "Brand")

	def test_rejects_incomplete(self):
		self.assertIsNone(ss.ThemeVariable.from_dict({"variable_name": "x"}))
		self.assertIsNone(ss.ThemeVariable.from_dict({"value": "#000"}))

	def test_invalid_type_falls_back_to_color(self):
		v = ss.ThemeVariable.from_dict({"name": "gap", "value": "8px", "type": "Nonsense"})
		self.assertEqual(v.type, "Color")


class TestSiteSpecFromLlm(unittest.TestCase):
	def _raw(self, **over):
		base = {
			"design_tokens": {
				"palette": {"primary": "#0af"},
				"variables": [
					{"variable_name": "brand-primary", "value": "#0af", "dark_value": "#08c"},
					{"variable_name": "", "value": "#fff"},  # dropped
				],
			},
			"fonts": {"heading": "Fraunces", "body": "DM Sans"},
			"nav": [{"label": "Home", "route": "/"}, {"label": "About", "route": "About"}, {"route": "/x"}],
			"header_brief": "sticky nav",
			"footer_brief": "three columns",
			"pages": [
				{"route": "/", "page_title": "Home", "brief": "hero"},
				{"route": "About", "title": "About"},
				{"route": "/", "page_title": "Dup Home"},  # dupe route → dropped
				{"page_title": "No Route"},  # invalid → dropped
			],
		}
		base.update(over)
		return base

	def test_parses_and_normalizes(self):
		spec = ss.SiteSpec.from_llm(self._raw())
		self.assertEqual([p.route for p in spec.pages], ["/", "/about"])
		self.assertEqual(spec.home_route, "/")
		self.assertEqual(len(spec.variables), 1)
		self.assertEqual(spec.variables[0].variable_name, "brand-primary")
		# nav route normalized, entry without label dropped
		self.assertEqual(spec.nav, [{"label": "Home", "route": "/"}, {"label": "About", "route": "/about"}])
		self.assertEqual(spec.fonts["heading"], "Fraunces")

	def test_caps_page_count(self):
		many = [{"route": f"/p{i}", "page_title": f"P{i}"} for i in range(20)]
		spec = ss.SiteSpec.from_llm(self._raw(pages=many))
		self.assertEqual(len(spec.pages), ss.MAX_PAGES)

	def test_rejects_empty(self):
		with self.assertRaises(ValueError):
			ss.SiteSpec.from_llm(self._raw(pages=[]))
		with self.assertRaises(ValueError):
			ss.SiteSpec.from_llm("not a dict")

	def test_roundtrip_json(self):
		spec = ss.SiteSpec.from_llm(self._raw())
		again = ss.SiteSpec.from_llm(spec.to_dict())
		self.assertEqual([p.route for p in again.pages], [p.route for p in spec.pages])


if __name__ == "__main__":
	unittest.main()
