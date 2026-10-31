"""read_skill: a skill's full guide, on demand (see builder/ai/skills)."""

from builder.ai.agent.registry import Tool
from builder.ai.skills import Skills


def run_read_skill(ctx, args: dict) -> str:
	name = (args.get("name") or "").strip()
	if name in ctx.attached_skills:
		return f"The {name} skill is already in your context this turn, in the page context message."
	if guide := Skills.read(name):
		return guide
	return f"FAILED: no skill '{name}'. Skills: {', '.join(Skills.names())}."


read_skill = Tool(
	name="read_skill",
	side="server",
	handler=run_read_skill,
	description=(
		"Read one of your skills, the full guide for a kind of work listed under Skills in your "
		"instructions. Read it before starting that work, in the same round as other reads."
	),
	parameters={
		"type": "object",
		"properties": {
			"name": {"type": "string", "enum": Skills.names(), "description": "The skill to read."}
		},
		"required": ["name"],
	},
)

TOOLS = [read_skill]
