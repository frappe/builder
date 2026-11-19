"""The look generated pages converge on, and what keeps Bob off it. Prompts can name
the stock look but not stop it (Bob renames the cream ground and moves to the next
favourite face), so it is checked in code."""

import colorsys
import re


def is_cream(colour: str) -> bool:
	"""A warm, pale, muted ground: the cream of the most common generated look."""
	match = re.fullmatch(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})", (colour or "").strip())
	if not match:
		return False
	digits = match.group(1)
	if len(digits) == 3:
		digits = "".join(c * 2 for c in digits)
	r, g, b = (int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4))
	hue, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
	return 20 <= hue * 360 <= 60 and lightness >= 0.85 and 0.15 <= saturation <= 0.8
