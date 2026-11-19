"""The look generated pages converge on, and what keeps Bob off it: the faces models
reach for by reflex, the cream ground, and random draws from the font catalogue and
from heroes and motion pages rarely get.
Prompts can name the stock look but not stop it (Bob renames the cream ground and
moves to the next favourite face), so it is checked and drawn in code."""

import colorsys
import json
import os
import random
import re
from functools import cache

import frappe

# Matched as family prefixes, so "Cormorant" covers Cormorant Garamond.
REFLEX_FACES = (
	"Fraunces",
	"Instrument Serif",
	"Instrument Sans",
	"DM Serif",
	"DM Sans",
	"Playfair Display",
	"Cormorant",
	"Lora",
	"Crimson",
	"Newsreader",
	"Space Grotesk",
	"Space Mono",
	"IBM Plex",
	"Syne",
	"Outfit",
	"Plus Jakarta Sans",
	"Inter",
	"Poppins",
	"Montserrat",
)
TIRED_FACES = ("Roboto", "Open Sans", "Raleway", "Merriweather")


def is_cream(colour: str) -> bool:
	"""A warm, pale, muted ground: the cream of the most common generated look, down to the
	sand a turned-back cream gets swapped for (#E9D8C1)."""
	match = re.fullmatch(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})", (colour or "").strip())
	if not match:
		return False
	digits = match.group(1)
	if len(digits) == 3:
		digits = "".join(c * 2 for c in digits)
	r, g, b = (int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4))
	hue, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
	return 20 <= hue * 360 <= 60 and lightness >= 0.8 and 0.15 <= saturation <= 0.8


def unseen_creams(ctx, colours) -> list[str]:
	"""Cream grounds a tool hasn't turned back yet this turn, marked as turned back now:
	the same value sent again is deliberate, so it passes."""
	seen = getattr(ctx, "stock_grounds", None)
	if seen is None:
		return []
	fresh = [colour for colour in dict.fromkeys(colours) if is_cream(colour) and colour.lower() not in seen]
	seen.update(colour.lower() for colour in fresh)
	return fresh


class FontDraw:
	"""A handful of Google Fonts families for one chat's new pages, drawn at random from
	the editor's own catalogue past its most popular head, without reflex or tired faces
	or families made for other scripts, icons or barcodes."""

	POPULAR_HEAD = 26  # the list opens with the most used families, then runs A-Z
	TEXT_FACES = 10
	DISPLAY_FACES = 6
	SKIP = re.compile(
		r"Noto|Icons|Symbols|Barcode|Emoji|^Flow |Redacted|\b(JP|KR|SC|TC|HK)\b|SIL|Kanadaka|"
		r"Telivigala|Tamil|Bangla|Devanagari|Gurmukhi|Hebrew|Arabic|Kufi|Naskh|Quran|Thai|Khmer|Lao|"
		r"Myanmar|Sinhala|Telugu|Kannada|Malayalam|Gujarati|Oriya|Tibetan|Ethiopic|Georgian|"
		r"Armenian|Mongolian|Tifinagh|Cherokee|Mincho|Ruwudu|^Anek (?!Latin)|^Zen |^M PLUS|^BIZ UD|"
		# Khmer and Japanese families: the catalogue carries no script, only names
		r"Hanuman|Battambang|Bokor|Siemreap|Moulpali|Koulen|Taprom|Dangrek|Freehand|Chenla|^Content$|"
		r"Odor Mean Chey|Suwannaphum|Fasthand|Bayon|Angkor|Kantumruy|Preahvihear|Nokora|^Moul$|Kdam|"
		r"Kaisei|Hina|Kosugi|Sawarabi|Shippori|Yuji|Klee|Yomogi|Hachi Maru|Mochiy|Murecho|Kiwi Maru|"
		r"Dela Gothic|RocknRoll|Potta One|Reggae One|Rampart One|^Stick$|Yusei|DotGothic|Train One|Darumadrop"
	)

	def __init__(self, seed: str | None):
		self.rng = random.Random(seed)

	def sentence(self) -> str:
		if not (faces := self.sample()):
			return ""
		return (
			f"This chat's draw from the Google Fonts catalogue, faces you'd rarely reach for: "
			f"{', '.join(faces)}. Take the heading face from it unless none fits the personality, "
			"and the body face too when one does."
		)

	def sample(self) -> list[str]:
		families = self.catalogue()
		text = [name for name, weights in families if weights >= 4]
		display = [name for name, weights in families if weights < 4]
		if len(text) < self.TEXT_FACES or len(display) < self.DISPLAY_FACES:
			return []
		return self.rng.sample(text, self.TEXT_FACES) + self.rng.sample(display, self.DISPLAY_FACES)

	@staticmethod
	@cache
	def catalogue() -> tuple[tuple[str, int], ...]:
		"""(family, upright weights) for every family worth drawing."""
		path = os.path.join(frappe.get_app_path("builder"), "..", "frontend", "src", "utils", "fontList.json")
		if not os.path.exists(path):
			return ()
		with open(path) as f:
			items = json.load(f)["items"][FontDraw.POPULAR_HEAD :]
		stock = REFLEX_FACES + TIRED_FACES
		return tuple(
			(item["family"], sum(not v.endswith("italic") for v in item["variants"]))
			for item in items
			if not FontDraw.SKIP.search(item["family"]) and not item["family"].startswith(stock)
		)


class CompositionDraw:
	"""A chat's starting points for the hero and the motion. Left to itself, every page
	opens on a headline beside a boxed photo, and given motion, drifts that photo."""

	HEROES = (
		"footage edge to edge behind the headline (search_videos; a photo when no clip fits)",
		"one photo edge to edge with the headline set over it on a scrim",
		"the headline as the image: display type filling the first screen, a photo cropped "
		"into a strip beneath it or knocked through the letters",
		"a collage of three photos at different scales and angles, overlapping around the headline",
		"a full-width strip of photos under a one-line headline, cropped at both edges",
		"one object staged huge and off-centre, the headline tucked into the space it leaves",
	)
	MOTIONS = (
		"footage looping silently",
		"a marquee band of the real offerings, names or places running at a steady pace",
		"the display headline tracking wider or scaling down as it leaves the first screen",
		"a row of photos sliding sideways as the page scrolls past it",
		"sections stacking over one another as they scroll (position:sticky, no script)",
		"one photo drifting slower than the page around it",
	)

	def __init__(self, seed: str | None):
		self.rng = random.Random(f"composition:{seed}")

	def sentence(self) -> str:
		heroes = self.rng.sample(self.HEROES, 2)
		motions = self.rng.sample(self.MOTIONS, 2)
		return (
			f"This chat's draw, to start from instead of the hero you'd reach for: a hero of "
			f"{heroes[0]}, or of {heroes[1]}; and for motion, {motions[0]}, or {motions[1]}. "
			"Take one of each unless the brand rules it out."
		)
