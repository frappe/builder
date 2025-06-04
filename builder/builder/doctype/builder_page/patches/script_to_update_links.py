# 1. update in global script
# <script defer data-api="https://frappecloud.com/api/event" data-domain="frappe.io" src="https://frappecloud.com/js/script.js"></script>
# 2. set blank header and footer from website settings
# 3. Update urls using following script from frappe console https://frappecloud.com/dashboard/benches/bench-1700/sites

import frappe

url_start = "pages/"
replace_url_start = ""


def update_block_href(blocks):
	for block in blocks:
		if (
			block.get("attributes")
			and block.get("attributes").get("href")
			and block.get("attributes").get("href").startswith(f"/{url_start}")
		):
			print(block.get("attributes").get("href"))
			block["attributes"]["href"] = block["attributes"]["href"].replace(url_start, replace_url_start)

		if "children" in block:
			update_block_href(block["children"])


def execute():
	pages = frappe.get_all(
		"Builder Page", fields=["name", "route", "blocks", "draft_blocks", "page_data_script"]
	)
	for page in pages:
		frappe.db.set_value(
			"Builder Page",
			page.name,
			"route",
			page.route.replace(url_start, replace_url_start),
			update_modified=False,
		)
		blocks = frappe.parse_json(page.get("blocks"))
		if blocks:
			update_block_href(blocks)
			frappe.db.set_value(
				"Builder Page",
				page.name,
				"blocks",
				frappe.as_json(blocks, indent=None),
				update_modified=False,
			)

		draft_blocks = frappe.parse_json(page.get("draft_blocks"))
		if draft_blocks:
			update_block_href(draft_blocks)
			frappe.db.set_value(
				"Builder Page",
				page.name,
				"draft_blocks",
				frappe.as_json(draft_blocks, indent=None),
				update_modified=False,
			)

		if page.page_data_script:
			page_data_script = page.page_data_script.replace(url_start, replace_url_start)
			frappe.db.set_value(
				"Builder Page", page.name, "page_data_script", page_data_script, update_modified=False
			)

	components = frappe.get_all("Builder Component", fields=["name", "block"])
	for component in components:
		component_block = frappe.parse_json(component.get("block"))
		if component_block:
			update_block_href([component_block])
			frappe.db.set_value(
				"Builder Component",
				component.name,
				"block",
				frappe.as_json(component_block, indent=None),
				update_modified=False,
			)


# def extend_with_component(block, extended_from_component, component_children):
# 	reset_block(block)
# 	for index, child in enumerate(block.get("children") or []):
# 		child["isChildOfComponent"] = extended_from_component
# 		component_child = component_children[index]
# 		if component_child:
# 			child["referenceBlockId"] = component_child.get("blockId")
# 			extend_with_component(child, extended_from_component, component_child.get("children"))

# def reset_with_component(block, extended_with_component, component_children):
# 	reset_block(block)
# 	block["children"] = []
# 	for component_child in component_children:
# 		block_component = get_block_copy(component_child)
# 		block_component["isChildOfComponent"] = extended_with_component
# 		block_component["referenceBlockId"] = component_child.get("blockId")
# 		child_block = block["children"].append(block_component)
# 		reset_with_component(child_block, extended_with_component, component_child.get("children"))

# def sync_block_with_component(parent_block, block, component_name, component_children):
# 	for component_child in component_children:
# 		block_exists = find_component_block(component_child.get("blockId"), parent_block.get("children"))
# 		if not block_exists:
# 			block_component = get_block_copy(component_child)
# 			block_component["isChildOfComponent"] = component_name
# 			block_component["referenceBlockId"] = component_child.get("blockId")
# 			reset_block(block_component)
# 			reset_with_component(block_component, component_name, component_child.get("children"))
# 			block["children"].append(block_component)

# 	for child in block.get("children") or []:
# 		component_child = component_children.find(lambda c: c.get("blockId") == child.get("referenceBlockId"))
# 		if component_child:
# 			sync_block_with_component(parent_block, child, component_name, component_child.get("children"))

# def find_component_block(block_id, blocks):
# 	for block in blocks:
# 		if block.get("referenceBlockId") == block_id:
# 			return block
# 		if block.get("children"):
# 			found = find_component_block(block_id, block.get("children"))
# 			if found:
# 				return found
# 	return None

# def reset_block(block, reset_children=True):
# 	block["blockId"] = block.generateId()
# 	block["baseStyles"] = {}
# 	block["rawStyles"] = {}
# 	block["mobileStyles"] = {}
# 	block["tabletStyles"] = {}
# 	block["attributes"] = {}
# 	block["customAttributes"] = {}
# 	block["classes"] = []

# 	if reset_children:
# 		for child in block.get("children") or []:
# 			reset_block(child, reset_children)
