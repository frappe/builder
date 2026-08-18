"""Domain skills for the generation step.

A skill is a focused art-direction playbook the agent attaches to a
generate_page call via the tool's `skill` parameter when the page's domain
matches. It rides into the generation messages on demand, so the base
generation prompt stays lean and unrelated builds pay nothing for it.
Adding a skill = one constant + one REGISTRY entry here, nothing else.
"""

from typing import ClassVar


class Skills:
	PORTFOLIO = """SKILL: PORTFOLIO — art direction for a personal/studio portfolio page. This playbook layers ON TOP of the system rules: where a generic default and this skill disagree, the skill wins; the brief's explicit decisions outrank both.

# What the page must do
A portfolio has one job: make a stranger remember this person and open the work. The WORK is the hero, the NAME is the brand, and the page itself is the proof of taste — for a designer, developer or photographer the page IS a work sample, so a safe template layout is a failed portfolio even when nothing is broken.

# Direction — commit to ONE persona
Read the discipline and mood from the brief, then commit fully to one direction instead of averaging them into "clean and modern" (the portfolio cliché). Strong pairings (layout system names from the base prompt):
- **The Index** — dense-utility: the whole page is a numbered ledger of work; name and one-line bio as a compact masthead; each project row carries index numeral, title, role, year. Generosity is WRONG here — precision is the luxury.
- **The Monograph** — editorial-grid: the person as a publication; oversized name masthead, kickers and folio numbers in the outer columns, each project an asymmetric spread with one dominant image.
- **The Poster** — poster-brutalist: for loud work (brand, type, motion); the name at 10vw+, projects as flat colour-blocked plates, hard rules, one rotated element.
- **The Stage** — single-object stage: for a photographer or 3D/visual artist; one work staged huge per section with a hairline spec-table caption (client, year, medium).
- **The Desk** — zine-collage: work scattered as taped prints at mixed scales and angles over one calm anchor; for illustrators and art directors.
- **The Split** — split-screen: a sticky identity pane (name, wordmark or treated portrait, contact) beside a scrolling work column; alternate the sticky side across sections.
When the brief names no direction, pick the one persona that fits the discipline — never default to a centered hero plus a card grid.

# The work index is the page's core section
- 3–6 projects, each with a real-sounding name, the person's role, a year, and ONE concrete outcome or detail ("cut checkout to one screen", "shot over three winters") — never "Project One", never a bare tech list.
- Give the index ONE layout idea executed perfectly: hairline ledger rows, alternating editorial spreads, a filmstrip of extreme crops (aspectRatio '21/9'), or numbered posters — not a uniform three-column grid of screenshot + title + tag pills.
- No real project imagery supplied? Stage typographic project PLATES (oversized index numeral, project name as display type, a flat brand-colour or duotone panel) — never fake browser screenshots, never laptop stock photos.

# Identity
- The page's SIGNATURE MOVE should be an identity move — the name itself as the device: footer wordmark at 14–18vw cropped by overflow hidden, a vertical spine (discipline or availability line in writingMode vertical-rl), the echo headline of their name, or the oversized numeral index over the work. Still exactly ONE, per the base rules.
- A 'Currently' line — one short row saying what they're doing now, where, and availability — reads more alive than any about-paragraph; prefer it over a second bio block.
- The portrait is treated as ART (duotone brand-wash, hard crop, offset echo panel) or absent entirely — never a floating circle headshot.
- Contact is a STATEMENT, not a form: one huge mailto line ('say hi → name@…') as its own section. Build a form only when the brief asks for one.

# Copy — first person, specific, zero portfolio clichés
BANNED, and everything that sounds like them: "passionate about", "crafting digital experiences", "pixel-perfect", "bringing ideas to life", "creative solutions", "I wear many hats", "let's build something amazing", "welcome to my portfolio". The about copy says something only this person could say — the brief's specifics verbatim (city, tools, obsession, oddity). Short lines; confident and a little dry beats enthusiastic.

# Portfolio anti-template assertions (each reads instantly as a template)
- NEVER the centered hero formula: "Hi, I'm X 👋 / I'm a [role] / [View work][Get in touch]".
- NEVER skill bars, percentage rings, tag-cloud pills, or a tools/logo carousel — competence is shown by the work index; at most a plain comma-separated tools line in the footer colophon.
- NEVER a stats band (years of experience / projects completed / happy clients).
- NEVER a testimonial slider or star ratings; one short quote set as an editorial pull-quote is the ceiling.
- NEVER identical project cards repeated in a uniform grid."""

	REGISTRY: ClassVar[dict[str, str]] = {"portfolio": PORTFOLIO}

	@classmethod
	def get(cls, name: str) -> str:
		return cls.REGISTRY.get((name or "").strip().lower(), "")

	@classmethod
	def names(cls) -> list[str]:
		return sorted(cls.REGISTRY)
