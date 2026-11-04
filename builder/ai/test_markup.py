import unittest

from builder.ai import markup
from builder.ai.block_codec import BlockCodec


def block(block_id, el="p", text="", children=(), **fields):
	return {"blockId": block_id, "element": el, "innerHTML": text, "children": list(children), **fields}


CARD = {"fontSize": "14px", "color": "var(--ink)", "lineHeight": "1.5", "letterSpacing": "0.02em"}


class TestLines(unittest.TestCase):
	def node(self, line: str) -> dict:
		return markup.load(line)[0]

	def test_reads_every_segment_of_a_line(self):
		node = self.node(
			'section.hero.dark [id=top alt="Two words"] "Hi \\"there\\"" {padding:96px 48px;background-color:$ink} '
			":hover{opacity:.9} t{gap:16px} m{padding:40px 16px} m:hover{opacity:1} // Hero"
		)

		self.assertEqual(node["el"], "section")
		self.assertEqual(node["classes"], ["hero", "dark"])
		self.assertEqual(node["attrs"], {"id": "top", "alt": "Two words"})
		self.assertEqual(node["text"], 'Hi "there"')
		self.assertEqual(
			node["style"],
			{"padding": "96px 48px", "backgroundColor": "var(--ink)", "hover:opacity": ".9"},
		)
		self.assertEqual(node["t_style"], {"gap": "16px"})
		self.assertEqual(node["m_style"], {"padding": "40px 16px", "hover:opacity": "1"})
		self.assertEqual(node["name"], "Hero")

	def test_keeps_separators_inside_parens_and_quotes(self):
		node = self.node(
			'div {background-image:url(data:image/svg+xml;utf8,<svg/>);grid-template-areas:"a b" "c d"}'
		)

		self.assertEqual(node["style"]["backgroundImage"], "url(data:image/svg+xml;utf8,<svg/>)")
		self.assertEqual(node["style"]["gridTemplateAreas"], '"a b" "c d"')

	def test_reads_the_calls(self):
		node = self.node(
			'div use(nav) props(active=home count=3 title="Hi there") bind(text=title src=props.image) if(show)'
		)

		self.assertEqual(node["component"], "nav")
		self.assertEqual(node["props"], {"active": "home", "count": 3, "title": "Hi there"})
		self.assertEqual(node["bind"], {"innerHTML": "title", "src": "props.image", "visible": "show"})

	def test_block_fields_written_as_css_move_where_they_belong(self):
		node = self.node('a {text:"Book now";href:/book;class:btn primary;color:red}')

		self.assertEqual(node["text"], "Book now")
		self.assertEqual(node["attrs"], {"href": "/book"})
		self.assertEqual(node["classes"], ["btn", "primary"])
		self.assertEqual(node["style"], {"color": "red"})

	def test_block_fields_written_as_key_value_on_the_line(self):
		node = self.node('a text:"Book: now" href:/book {color:red}')

		self.assertEqual((node["el"], node["text"], node["attrs"]), ("a", "Book: now", {"href": "/book"}))
		self.assertEqual(
			markup.parse_ops('@a1b2 text:"" {display:none}')[0].fields,
			{"text": "", "style": {"display": "none"}},
		)

	def test_a_property_that_is_not_css_is_an_error(self):
		with self.assertRaises(markup.MarkupError):
			self.node("p {font size:12px}")

	def test_attributes_stay_strings(self):
		self.assertEqual(
			self.node("input [required=true rows=5]")["attrs"], {"required": "true", "rows": "5"}
		)

	def test_an_icon_and_a_tagless_line(self):
		self.assertEqual(self.node("icon(arrow-right) {width:20px}")["icon"], "arrow-right")
		self.assertNotIn("el", self.node('"Just text"'))

	def test_a_repeater_takes_its_first_child_as_the_item(self):
		node = self.node('div repeat(dishes=[{"name":"Ramen"}])\n  article\n    h3 bind(text=name)')

		self.assertEqual(node["repeat"]["data"], "dishes")
		self.assertEqual(node["repeat"]["items"], [{"name": "Ramen"}])
		self.assertEqual(node["repeat"]["item"]["el"], "article")

	def test_a_raw_script_body_belongs_to_the_block_above(self):
		node = self.node(
			"div use(tabs)\n  js |\n    const a = 1;\n      nested();\n  css |\n    .a { color: red; }"
		)

		self.assertEqual(
			node["client_script"], {"js": "const a = 1;\n  nested();", "css": ".a { color: red; }"}
		)

	def test_a_text_line_under_a_block_folds_into_it(self):
		root = self.node(
			'div\n  h1 {font-size:80px}\n    "Ramen after dark." {color:$bone}\n  p\n    "One"\n    "two"\n    span "kept"'
		)

		h1, p = root["c"]
		self.assertEqual(
			(h1["text"], h1["style"]), ("Ramen after dark.", {"fontSize": "80px", "color": "var(--bone)"})
		)
		self.assertNotIn("c", h1)
		self.assertEqual((p["text"], [c["el"] for c in p["c"]]), ("One two", ["span"]))

	def test_a_pug_text_line_folds_into_the_block_above(self):
		root = self.node("div\n  h3 {font-size:25px}\n    | Morning Hatha")

		self.assertEqual(root["c"][0]["text"], "Morning Hatha")

	def test_a_generated_line_keeps_its_text_past_a_bad_segment(self):
		errors = []
		node = markup.load('div\n  p $nope "A four-week introduction"} {color:red}', errors=errors)[0]["c"][0]

		self.assertEqual((node["text"], node["style"]), ("A four-week introduction", {"color": "red"}))
		self.assertEqual(len(errors), 2)

	def test_a_set_takes_a_state_and_a_space_before_the_brace(self):
		root = self.node("$btn {color:red}\n$btn:hover {color:blue}\na $btn :hover {opacity:.9}")

		self.assertEqual(root["style"], {"color": "red", "hover:color": "blue", "hover:opacity": ".9"})

	def test_a_comment_line_is_skipped(self):
		root = self.node('div\n  // the hero\n  h1 "A" // Title')

		self.assertEqual([(c["el"], c.get("name")) for c in root["c"]], [("h1", "Title")])

	def test_indentation_nests(self):
		root = self.node('div\n  section\n    h1 "A"\n  section\n    p "B"')

		self.assertEqual([c["c"][0]["text"] for c in root["c"]], ["A", "B"])

	def test_a_bad_line_raises_unless_errors_are_collected(self):
		with self.assertRaises(markup.MarkupError):
			markup.load('p "unclosed')
		errors = []
		roots = markup.load('p "unclosed\np "ok"', errors=errors)
		self.assertEqual([r["text"] for r in roots], ["unclosed", "ok"])
		self.assertIn("unclosed string", errors[0])


class TestStyleSets(unittest.TestCase):
	def test_a_set_spreads_under_the_lines_own_declarations(self):
		root = markup.load("$label {font-size:11px;color:$ink} m{font-size:10px}\np $label {color:red}")[0]

		self.assertEqual(root["style"], {"fontSize": "11px", "color": "red"})
		self.assertEqual(root["m_style"], {"fontSize": "10px"})

	def test_an_undefined_set_is_an_error(self):
		with self.assertRaises(markup.MarkupError):
			markup.load("p $nope")

	def test_reading_factors_repeated_declarations_into_a_set(self):
		page = block(
			"root", "div", children=[block(f"p{i}", text=f"t{i}", baseStyles=dict(CARD)) for i in range(3)]
		)
		sets: dict = {}

		text = markup.dump_block(page, sets=sets)

		self.assertTrue(text.startswith("$s1 {"))
		self.assertIn('@p0 p $s1 "t0"', text)
		self.assertEqual(sets["s1"]["style"], CARD)

	def test_a_shorthand_twin_keeps_a_block_out_of_the_set(self):
		shared = {**CARD, "border": "1px solid"}
		twin = {"borderBottom": "none", **shared}
		page = block(
			"root",
			"div",
			children=[
				block("a", baseStyles=shared),
				block("b", baseStyles=shared),
				block("c", baseStyles=twin),
			],
		)

		line = next(row for row in markup.dump_block(page).split("\n") if row.strip().startswith("@c"))

		self.assertIn("border-bottom:none", line)
		self.assertIn("border:1px solid", line)


class TestRoundTrip(unittest.TestCase):
	def test_a_page_reads_back_to_the_same_styles_text_and_attributes(self):
		page = block(
			"root",
			"div",
			baseStyles={"display": "flex", "fontFamily": "var(--acme-font)"},
			children=[
				block(
					"h",
					"h1",
					"Slow mornings",
					baseStyles={"fontSize": "88px", "hover:color": "#fff"},
					mobileStyles={"fontSize": "44px"},
				),
				*[
					block(f"c{i}", "a", f"Card {i}", baseStyles=dict(CARD), attributes={"href": f"/c{i}"})
					for i in range(4)
				],
				block(
					"i",
					"svg",
					"<svg/>",
					customAttributes={"data-lucide": "star"},
					baseStyles={"width": "20px"},
				),
			],
		)
		node = BlockCodec.compress(page)

		back = markup.load(markup.Dumper().dump(node))[0]

		for original, parsed in zip(node["c"], back["c"], strict=True):
			self.assertEqual(parsed.get("style"), original.get("style"))
			self.assertEqual(parsed.get("text"), original.get("text"))
			self.assertEqual(parsed.get("attrs"), original.get("attrs"))
		self.assertEqual(back["c"][-1]["icon"], "star")

	def test_short_refs_are_unique_prefixes(self):
		page = block("root", "div", children=[block("k3x9abcde"), block("k3x9fghij"), block("zzzz11111")])

		refs = markup.short_refs(page)

		self.assertEqual(refs["zzzz11111"], "zzzz")
		self.assertEqual({refs["k3x9abcde"], refs["k3x9fghij"]}, {"k3x9a", "k3x9f"})

	def test_an_outline_drops_styles_and_clips_text(self):
		page = block("root", "div", children=[block("a", text="x" * 80, baseStyles=dict(CARD))])

		text = markup.dump_block(page, styles=False, max_text=10)

		self.assertIn('@a p "xxxxxxxxx…"', text)
		self.assertNotIn("{", text)


class TestOps(unittest.TestCase):
	def test_reads_each_op(self):
		ops = markup.parse_ops(
			"@a @b {margin-top:} [-href]\n"
			'add after @a\n  section\n    h2 "New"\n'
			"remove @c @d\n"
			"move @e to @f 0\n"
			"move @e before @g\n"
			"replace @h\n  div\n"
		)

		self.assertEqual([op.kind for op in ops], ["patch", "add", "remove", "move", "move", "replace"])
		self.assertEqual(ops[0].refs, ["a", "b"])
		self.assertEqual(ops[0].fields, {"style": {"marginTop": None}, "attrs": {"href": None}})
		self.assertEqual(ops[1].where, ("after", "a", None))
		self.assertEqual(ops[1].body[0]["c"][0]["text"], "New")
		self.assertEqual(ops[3].where, ("into", "f", 0))
		self.assertEqual(ops[4].where, ("before", "g", None))

	def test_a_patch_takes_its_text_from_the_line_below(self):
		op = markup.parse_ops('@a {color:red}\n  "New text"')[0]

		self.assertEqual(op.fields, {"style": {"color": "red"}, "text": "New text"})

	def test_comment_lines_are_not_ops(self):
		self.assertEqual([op.kind for op in markup.parse_ops('// set the CTA\n@a "x"\n# done')], ["patch"])

	def test_a_bad_op_carries_its_error_and_the_rest_still_parse(self):
		ops = markup.parse_ops('@a {color:red\nmove @b nowhere\n@c "ok"')

		self.assertEqual([op.kind for op in ops], ["error", "error", "patch"])
		self.assertIn("line 1", ops[0].error)

	def test_sets_defined_in_a_script_or_seeded_apply_to_later_ops(self):
		ops = markup.parse_ops("$x {color:red}\n@a $x $seeded", sets={"seeded": {"style": {"gap": "4px"}}})

		self.assertEqual(ops[0].fields["style"], {"color": "red", "gap": "4px"})


if __name__ == "__main__":
	unittest.main()
