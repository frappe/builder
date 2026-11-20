"""Skills: guides Bob reads only for the work they cover, so the system prompt sent
on every round stays small. One markdown file per skill in this folder; the system
prompt carries just each skill's frontmatter `description` (see Skills.index), and
read_skill, or the loop for a state it can see, puts the body in front of the model."""

import os
import re

from builder.ai.stock_look import REFLEX_FACES, TIRED_FACES, FontDraw

SLOT = re.compile(r"\{\{(\w+)\}\}")
# Text a skill takes at read time: what changes per chat, or what code owns.
SLOTS = {
	"font_draw": lambda seed: FontDraw(seed).sentence(),
	"stock_faces": lambda seed: ", ".join(REFLEX_FACES + TIRED_FACES),
}


class Skills:
	DIR = os.path.dirname(__file__)

	@classmethod
	def index(cls) -> str:
		lines = [f"- {name}: {cls.parse(name)[0]['description']}" for name in cls.names()]
		return (
			"# Skills\n"
			"Full guides for kinds of work, read with read_skill before that work (one already in "
			"your context this turn needs no read):\n" + "\n".join(lines)
		)

	@classmethod
	def read(cls, name: str, seed: str | None = None) -> str | None:
		"""A skill's guide, its slots filled; `seed` keeps a chat's draws the same across turns."""
		if name not in cls.names():
			return None
		fill = lambda match: SLOTS[match.group(1)](seed) if match.group(1) in SLOTS else match.group(0)  # noqa: E731
		return SLOT.sub(fill, cls.parse(name)[1])

	@classmethod
	def names(cls) -> list[str]:
		return sorted(file[:-3] for file in os.listdir(cls.DIR) if file.endswith(".md"))

	@classmethod
	def parse(cls, name: str) -> tuple[dict, str]:
		if name not in cls.names():
			raise ValueError(f"Unknown skill: {name}")
		# Only exact filenames from this package's skill directory reach the file read.
		with open(os.path.join(cls.DIR, f"{name}.md")) as f:  # nosemgrep: frappe-security-file-traversal
			_, head, body = f.read().split("---\n", 2)
		meta = dict(line.split(": ", 1) for line in head.strip().splitlines())
		return meta, body.strip()
