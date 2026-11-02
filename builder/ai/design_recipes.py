"""Optional composition recipes; parameters remain ordinary editable Builder blocks."""

import html

RECIPES = {
	"editorial": {
		"label": "Editorial story",
		"fits": "Narrative, portfolios, publications",
		"layout": "editorial",
	},
	"split": {
		"label": "Image and story",
		"fits": "A strong portrait, place or product image",
		"layout": "split",
	},
	"compact": {
		"label": "Clear and direct",
		"fits": "Professional services, dense information, one clear action",
		"layout": "compact",
	},
	"stage": {
		"label": "Product stage",
		"fits": "One distinctive object or product with an owned image",
		"layout": "stage",
	},
}


def text_block(element, text, style=None):
	return {"el": element, "text": html.escape(str(text or "")), "style": style or {}}


def compose_direction(spec: dict, brief: dict, image_url: str | None = None) -> dict:
	recipe = spec.get("recipe", "editorial")
	if recipe not in RECIPES:
		raise ValueError("Choose a known recipe or supply candidate YAML")
	palette = spec.get("palette") or {}
	background, ink, accent = (
		palette.get("background", "#faf8f3"),
		palette.get("text", "#222222"),
		palette.get("accent", "#734133"),
	)
	font = spec.get("font") or "Inter"
	title = spec.get("headline") or brief.get("project")
	if not title:
		raise ValueError("A direction needs the user's real project name or supplied headline")
	copy = spec.get("description") or brief.get("content") or brief.get("goal") or ""
	hero_copy = {
		"el": "div",
		"style": {"display": "flex", "flexDirection": "column", "justifyContent": "center", "gap": "24px"},
		"c": [
			text_block("p", brief.get("project", title), {"fontSize": "14px", "letterSpacing": "0.08em"}),
			text_block(
				"h1",
				title,
				{
					"fontSize": "68px" if recipe != "compact" else "44px",
					"lineHeight": "1.05",
					"fontWeight": "600",
					"maxWidth": "16ch",
				},
			),
			text_block("p", copy, {"fontSize": "18px", "lineHeight": "1.6", "maxWidth": "52ch"}),
		],
	}
	hero_copy["c"][1]["m_style"] = {"fontSize": "38px"}
	if spec.get("action"):
		hero_copy["c"].append(
			{
				**text_block(
					"a",
					spec["action"],
					{
						"backgroundColor": accent,
						"color": "#ffffff",
						"padding": "14px 22px",
						"borderRadius": "4px",
						"alignSelf": "flex-start",
					},
				),
				"attrs": {"href": spec.get("action_url") or "#details"},
			}
		)
	children = [hero_copy]
	if image_url:
		image = {
			"el": "img",
			"attrs": {"src": image_url, "alt": spec.get("image_description") or ""},
			"style": {
				"width": "100%",
				"height": "540px",
				"objectFit": "cover",
				"objectPosition": spec.get("focal_point", "50% 50%"),
			},
			"m_style": {"height": "330px"},
		}
		children.insert(0 if recipe == "editorial" else 1, image)
	columns = "1fr 1fr" if image_url and recipe in {"split", "stage"} else "1fr"
	hero = {
		"el": "section",
		"style": {
			"display": "grid",
			"gridTemplateColumns": columns,
			"gap": "48px",
			"padding": "64px",
			"maxWidth": "1440px",
			"margin": "0 auto",
		},
		"m_style": {"gridTemplateColumns": "1fr", "padding": "28px", "gap": "28px"},
		"c": children,
	}
	section = {
		"el": "section",
		"attrs": {"id": "details"},
		"style": {
			"borderTop": f"1px solid {ink}",
			"padding": "48px 64px",
			"display": "grid",
			"gridTemplateColumns": "1fr 2fr",
			"gap": "32px",
		},
		"m_style": {"padding": "28px", "gridTemplateColumns": "1fr"},
		"c": [
			text_block("h2", spec.get("section_title") or brief.get("goal") or "About", {"fontSize": "28px"}),
			text_block("p", spec.get("section_copy") or copy, {"fontSize": "18px", "lineHeight": "1.6"}),
		],
	}
	return {
		"el": "div",
		"style": {"backgroundColor": background, "color": ink, "fontFamily": font},
		"c": [hero, section],
	}
