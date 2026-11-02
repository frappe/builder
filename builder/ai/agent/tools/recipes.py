import json
from pathlib import Path

from builder.ai.agent.registry import Tool

RECIPES = {
	"reveal": {
		"markup": "Add attributes: {'data-bob-reveal': ''} to the selected content blocks. Keep all content visible in base styles.",
		"script": "motion.js",
		"checks": [
			"Content visible without JavaScript",
			"No active animations under reduced motion",
			"No duplicate observers after reload",
		],
	},
	"tabs": {
		"markup": "Use a wrapper with data-bob-tabs. Inside it, a role=tablist contains button role=tab elements with unique id and aria-controls pointing to their panel id. Each panel has role=tabpanel and aria-labelledby pointing to its tab. Panels are visible in base markup; JS progressively hides inactive panels.",
		"script": "tabs.js",
		"checks": [
			"Click each tab",
			"Arrow keys and Home/End move focus and selection",
			"Every panel visible without JavaScript",
			"No duplicate listeners on reload",
		],
	},
	"disclosure": {
		"yaml": {
			"el": "details",
			"c": [{"el": "summary", "text": "Your question"}, {"el": "p", "text": "Your answer"}],
		},
		"checks": ["Mouse, touch, Enter and Space toggle the native disclosure", "Focus remains visible"],
		"script": None,
	},
}


def read_recipe(ctx, args):
	name = args.get("name")
	if not name:
		return json.dumps(
			{
				"recipes": list(RECIPES),
				"guidance": "Retrieve one relevant recipe. Preserve content and choose movement only when requested.",
			}
		)
	value = dict(RECIPES[name])
	if file := value.pop("script", None):
		value["javascript"] = Path(__file__).parents[2].joinpath("browser", file).read_text()
	return json.dumps(value)


TOOLS = [
	Tool(
		name="get_interaction_recipe",
		side="server",
		description="Retrieve a small accessible interaction/motion recipe and its verification checklist: native disclosure, keyboard tabs, or reduced-motion-aware reveal. Apply returned JS using the normal script tools after its markup exists.",
		parameters={"type": "object", "properties": {"name": {"type": "string", "enum": list(RECIPES)}}},
		handler=read_recipe,
	)
]
