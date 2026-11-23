"""How far an edit on the open page reaches, told to a run whose hosting app withheld every tool that could find
out (frappe.page's own site keeps run_python, query_records and get_document from Bob).

His asking rules for an edit past the open page (prompts.py, the components skill) have him search the site's
pages and quote how many pages, and how many live, a component sits on. Without those tools he can measure none
of it, so here he hears it counted: a scope question then quotes real numbers, and where nothing reaches past
this page there is no question to ask."""

import frappe

from builder.ai.agent.selectors import walk_blocks
from builder.utils import is_component_used

SEARCH_TOOLS = frozenset({"run_python", "query_records", "get_document"})
# past this the list would crowd every turn's context, and the count would read every page's blocks each turn
MAX_PAGES = 12
UNCOUNTED = (
	"You can't search or count the site's other pages here: a scope question names the scopes "
	"(this page, or the component everywhere) without numbers."
)
ONLY_PAGE = (
	"This page is the site's only Builder page, so no edit here reaches another page: there is no scope "
	"to ask about."
)
ALL_HERE = "Every component on this page is on this page only, so an edit to one reaches no other page."
PAGE_FIELDS = ["name", "page_title", "route", "published", "staging", "blocks", "draft_blocks"]


def reach_context(page_id: str | None, root: dict | None, withheld) -> str:
	if not page_id or not SEARCH_TOOLS <= set(withheld):
		return ""
	pages = frappe.get_list("Builder Page", fields=PAGE_FIELDS, order_by="creation asc", limit=MAX_PAGES + 1)
	if len(pages) > MAX_PAGES:
		return UNCOUNTED
	others = [page for page in pages if page.name != page_id]
	if not others:
		return ONLY_PAGE
	return " ".join(part for part in (other_pages(others), component_reach(page_id, root, pages)) if part)


def other_pages(others: list) -> str:
	listed = "; ".join(
		f"'{page.page_title or page.name}' (id {page.name}, /{(page.route or '').lstrip('/')}, {state(page)})"
		for page in others
	)
	count = f"{len(others)} Builder page{'s' if len(others) > 1 else ''}"
	return f"Besides this page the site has {count}: {listed}. read_page reads any of them by id."


def component_reach(page_id: str, root: dict | None, pages: list) -> str:
	embedded = sorted(
		{
			block["extendedFromComponent"]
			for block, _ in walk_blocks(root)
			if block.get("extendedFromComponent")
		}
	)
	if not embedded:
		return ""
	reach = {
		component: [page for page in pages if page.name != page_id and embeds(page, component)]
		for component in embedded
	}
	if not any(reach.values()):
		return ALL_HERE
	here = [page for page in pages if page.name == page_id]
	counts = "; ".join(
		f"{component} {placement(here + elsewhere) if elsewhere else 'on this page only'}"
		for component, elsewhere in reach.items()
	)
	return (
		f"Where the components on this page are embedded: {counts}. These are the counts a scope question "
		"quotes; an edit that reaches no page but this one has nothing to ask about."
	)


def placement(pages: list) -> str:
	live = sum(1 for page in pages if page.published)
	staging = sum(1 for page in pages if page.staging and not page.published)
	return f"on {len(pages)} pages ({live} live{f', {staging} staging' if staging else ''})"


def embeds(page, component: str) -> bool:
	return any(field and is_component_used(field, component) for field in (page.blocks, page.draft_blocks))


def state(page) -> str:
	return "live" if page.published else "staging" if page.staging else "draft"
