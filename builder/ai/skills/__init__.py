"""Skills: guides Bob reads only for the work they cover, so the system prompt sent
on every round stays small. One markdown file per skill in this folder; the system
prompt carries just each skill's frontmatter `description` (see Skills.index), and
read_skill, or the loop for a state it can see, puts the body in front of the model."""

import os


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
	def read(cls, name: str) -> str | None:
		return cls.parse(name)[1] if name in cls.names() else None

	@classmethod
	def names(cls) -> list[str]:
		return sorted(file[:-3] for file in os.listdir(cls.DIR) if file.endswith(".md"))

	@classmethod
	def parse(cls, name: str) -> tuple[dict, str]:
		with open(os.path.join(cls.DIR, f"{name}.md")) as f:
			_, head, body = f.read().split("---\n", 2)
		meta = dict(line.split(": ", 1) for line in head.strip().splitlines())
		return meta, body.strip()
