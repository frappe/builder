
import frappe


def update_prop_options(blocks):
	for block in blocks:
		if block.get("props"):
			for prop in block["props"].keys():
				if("standardOptions" in block["props"][prop]):
					block["props"][prop]["propOptions"] = block["props"][prop]["standardOptions"]
					del block["props"][prop]["standardOptions"]
		if "children" in block and block.get("children"):
			update_prop_options(block["children"])

def execute():
	pages = frappe.get_all(
		"Builder Page", fields=["name", "route", "blocks", "draft_blocks"]
	)
	for page in pages:
		blocks = frappe.parse_json(page.get("blocks"))
		if blocks:
			update_prop_options(blocks)
			frappe.db.set_value(
				"Builder Page",
				page.name,
				"blocks",
				frappe.as_json(blocks, indent=None),
				update_modified=False,
			)

		draft_blocks = frappe.parse_json(page.get("draft_blocks"))
		if draft_blocks:
			update_prop_options(draft_blocks)
			frappe.db.set_value(
				"Builder Page",
				page.name,
				"draft_blocks",
				frappe.as_json(draft_blocks, indent=None),
				update_modified=False,
			)

	components = frappe.get_all("Builder Component", fields=["name", "block"])
	for component in components:
		component_block = frappe.parse_json(component.get("block"))
		if component_block:
			update_prop_options([component_block])
			frappe.db.set_value(
				"Builder Component",
				component.name,
				"block",
				frappe.as_json(component_block, indent=None),
				update_modified=False,
			)
