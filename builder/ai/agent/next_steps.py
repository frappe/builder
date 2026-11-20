"""Next steps Bob suggests after finishing work. The model ends its reply with
<next>…</next> lines; the chat shows them as buttons the user can send, so they are
held back from the live stream and stored apart from the reply's text."""

import re

OPEN = "<next>"
STEP = re.compile(r"<next>(.*?)(?:</next>|$)", re.S)
MAX_STEPS = 3
MAX_LENGTH = 90


def split(text: str) -> tuple[str, list[str]]:
	"""The reply without its next-step tags, and the steps they held."""
	steps = [" ".join(step.split()) for step in STEP.findall(text or "")]
	steps = [step for step in steps if 0 < len(step) <= MAX_LENGTH][:MAX_STEPS]
	return STEP.sub("", text or "").rstrip(), steps


def visible(text: str) -> str:
	"""What the chat may show of a reply still being written: everything before the
	first tag, holding back an ending that could still turn into one."""
	if (at := text.find(OPEN)) != -1:
		return text[:at]
	for size in range(min(len(OPEN) - 1, len(text)), 0, -1):
		if OPEN.startswith(text[-size:]):
			return text[:-size]
	return text
