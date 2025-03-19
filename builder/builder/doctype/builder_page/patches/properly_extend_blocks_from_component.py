import frappe


def execute():
	"""Properly extend blocks from component"""
	web_pages = frappe.get_all("Builder Page", fields=["name", "blocks"])
	for web_page in web_pages:
		blocks = frappe.parse_json(web_page.blocks)
		if blocks:
			update_blocks(blocks)
			frappe.db.set_value(
				"Builder Page",
				web_page.name,
				"blocks",
				frappe.as_json(blocks, indent=None),
				update_modified=False,
			)
		draft_blocks = frappe.parse_json(web_page.draft_blocks)
		if draft_blocks:
			update_blocks(draft_blocks)
			frappe.db.set_value(
				"Builder Page",
				web_page.name,
				"draft_blocks",
				frappe.as_json(blocks, indent=None),
				update_modified=False,
			)


def update_blocks(blocks):
	for block in blocks:
		block["baseStyles"] = convert_dict_keys_to_camel_case(block.get("baseStyles", {}))
		block["tabletStyles"] = convert_dict_keys_to_camel_case(block.get("tabletStyles", {}))
		block["mobileStyles"] = convert_dict_keys_to_camel_case(block.get("mobileStyles", {}))

		if block.get("extendedFromComponent"):
			try:
				component = frappe.get_cached_doc("Builder Component", block.get("extendedFromComponent"))
				component_block = frappe.parse_json(component.get("block"))
				update_blocks([component_block])
				frappe.db.set_value(
					"Builder Component",
					component.name,
					"block",
					frappe.as_json(component_block, indent=None),
					update_modified=False,
				)
				extend_block_from_component(
					block, component.name, component_block.get("children"), component_block
				)
			except frappe.DoesNotExistError:
				frappe.log_error(f"Builder Component {block.get('extendedFromComponent')} not found")

		if "children" in block:
			update_blocks(block["children"])


def extend_block_from_component(block, extended_from_component, children, component_block):
	block["blockId"] = generate_id()
	block["baseStyles"] = get_dict_difference(component_block["baseStyles"], block["baseStyles"])
	block["mobileStyles"] = get_dict_difference(component_block["mobileStyles"], block["mobileStyles"])
	block["tabletStyles"] = get_dict_difference(component_block["tabletStyles"], block["tabletStyles"])
	block["attributes"] = get_dict_difference(component_block["attributes"], block["attributes"])
	if block.get("innerHTML") and block.get("innerHTML") == component_block.get("innerHTML"):
		del block["innerHTML"]
	if block.get("element") and block.get("element") == component_block.get("element"):
		del block["element"]

	if "children" in block:
		for index, child in enumerate(block["children"]):
			child["isChildOfComponent"] = extended_from_component
			if children and index < len(children):
				if component_child := children[index]:
					child["referenceBlockId"] = component_child["blockId"]
					extend_block_from_component(
						child, extended_from_component, component_child["children"], component_child
					)


def generate_id():
	return frappe.generate_hash("", 10)


def get_dict_difference(dict_1, dict_2):
	dict_1 = convert_dict_keys_to_camel_case(dict_1)
	dict_2 = convert_dict_keys_to_camel_case(dict_2)
	return {key: dict_2[key] for key in dict_2 if key not in dict_1 or dict_1[key] != dict_2[key]}


def convert_dict_keys_to_camel_case(dict_):
	sorted_keys = sorted(dict_.keys(), key=lambda x: x.islower())
	sorted_dict = {key: dict_[key] for key in sorted_keys}
	return {kebab_to_camel_case(key): value for key, value in sorted_dict.items()}


def kebab_to_camel_case(string):
	# font-size -> fontSize
	# height -> height
	return "".join(word.capitalize() if index > 0 else word for index, word in enumerate(string.split("-")))
