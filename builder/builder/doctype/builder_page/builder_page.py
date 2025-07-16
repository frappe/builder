# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

import copy
import os
import shutil

import bs4 as bs
import frappe
import frappe.utils
from frappe.modules import scrub
from frappe.modules.export_file import export_to_files
from frappe.utils.caching import redis_cache
from frappe.utils.jinja import render_template
from frappe.website.page_renderers.document_page import DocumentPage
from frappe.website.path_resolver import evaluate_dynamic_routes
from frappe.website.path_resolver import resolve_path as original_resolve_path
from frappe.website.serve import get_response_content
from frappe.website.utils import clear_cache
from frappe.website.website_generator import WebsiteGenerator
from jinja2.exceptions import TemplateSyntaxError

from builder.hooks import builder_path
from builder.html_preview_image import generate_preview
from builder.utils import (
	ColonRule,
	camel_case_to_kebab_case,
	clean_data,
	copy_img_to_asset_folder,
	escape_single_quotes,
	execute_script,
	get_builder_page_preview_file_paths,
	get_template_assets_folder_path,
	is_component_used,
	split_styles,
)

MOBILE_BREAKPOINT = 576
TABLET_BREAKPOINT = 768
DESKTOP_BREAKPOINT = 1024


class BuilderPageRenderer(DocumentPage):
	def can_render(self):
		if page := find_page_with_path(self.path):
			self.doctype = "Builder Page"
			self.docname = page
			self.validate_access()
			return True

		for d in get_web_pages_with_dynamic_routes():
			try:
				if evaluate_dynamic_routes([ColonRule(f"/{d.route}", endpoint=d.name)], self.path):
					self.doctype = "Builder Page"
					self.docname = d.name
					self.validate_access()
					return True
			except ValueError:
				return False

		return False

	def validate_access(self):
		if self.docname:
			self.doc = frappe.get_cached_doc(self.doctype, self.docname)
			if self.doc.authenticated_access and frappe.session.user == "Guest":
				raise frappe.PermissionError("Please log in to view this page.")

	def set_canonical_url(self):
		if not self.doc:
			return
		context = getattr(self, "context", frappe._dict())
		if self.doc.is_home_page():
			context.canonical_url = frappe.utils.get_url()
		elif self.doc.canonical_url:
			context.canonical_url = render_template(self.doc.canonical_url, context)
		else:
			context.canonical_url = frappe.utils.get_url(self.path)
		self.context = context

	def set_missing_values(self):
		self.set_canonical_url()


class BuilderPage(WebsiteGenerator):
	def onload(self):
		self.set_onload("builder_path", builder_path)

	website = frappe._dict(
		template="templates/generators/webpage.html",
		condition_field="published",
		page_title_field="page_title",
	)

	def autoname(self):
		if not self.name:
			self.name = f"page-{frappe.generate_hash(length=8)}"

	def before_insert(self):
		self.process_blocks()
		self.set_preview()
		self.set_default_values()

	def process_blocks(self):
		for block_type in ["blocks", "draft_blocks"]:
			if isinstance(getattr(self, block_type), list):
				setattr(self, block_type, frappe.as_json(getattr(self, block_type), indent=None))
		if not self.blocks:
			self.blocks = "[]"

	def set_preview(self):
		if not self.preview:
			self.preview = "/assets/builder/images/fallback.png"
		else:
			self.flags.skip_preview = True

	def set_default_values(self):
		if not self.page_title:
			self.page_title = "My Page"
		if not self.route:
			if not self.name:
				self.autoname()
			self.route = f"pages/{self.name}"

	def on_update(self):
		if self.has_value_changed("route"):
			if ":" in self.route or "<" in self.route:
				self.db_set("dynamic_route", 1)
			else:
				self.db_set("dynamic_route", 0)

		if (
			self.has_value_changed("dynamic_route")
			or self.has_value_changed("route")
			or self.has_value_changed("published")
			or self.has_value_changed("disable_indexing")
			or self.has_value_changed("blocks")
		):
			self.clear_route_cache()

		if self.has_value_changed("published") and not self.published:
			# if this is homepage then clear homepage from builder settings
			if frappe.get_cached_value("Builder Settings", None, "home_page") == self.route:
				frappe.db.set_value("Builder Settings", None, "home_page", None)

		if frappe.conf.developer_mode and self.is_template:
			save_as_template(self)

	def clear_route_cache(self):
		get_web_pages_with_dynamic_routes.clear_cache()
		find_page_with_path.clear_cache()
		clear_cache(self.route)

	def on_trash(self):
		if self.is_template and frappe.conf.developer_mode:
			page_template_folder = os.path.join(
				frappe.get_app_path("builder"), "builder", "builder_page_template", scrub(self.name)
			)
			if os.path.exists(page_template_folder):
				shutil.rmtree(page_template_folder)
			assets_path = get_template_assets_folder_path(self)
			if os.path.exists(assets_path):
				shutil.rmtree(assets_path)

	def add_comment(self, comment_type="Comment", text=None, comment_email=None, comment_by=None):
		if comment_type in ["Attachment Removed", "Attachment"]:
			return

		super().add_comment(
			comment_type=comment_type,
			text=text,
			comment_email=comment_email,
			comment_by=comment_by,
		)

	@frappe.whitelist()
	def publish(self, route_variables=None):
		if route_variables:
			frappe.form_dict.update(frappe.parse_json(route_variables or "{}"))
		self.published = 1
		if self.draft_blocks:
			self.blocks = self.draft_blocks
			self.draft_blocks = None
		self.save()
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"generate_page_preview_image",
			queue="short",
			enqueue_after_commit=True,
		)

		return self.route

	@frappe.whitelist()
	def unpublish(self, **kwargs):
		self.published = 0
		self.save()

	def get_context(self, context):
		# delete default favicon
		del context.favicon
		context.disable_indexing = self.disable_indexing
		page_data = self.get_page_data()
		if page_data.get("title"):
			context.title = page_data.get("page_title")

		blocks = self.blocks
		context.preview = frappe.flags.for_preview

		if self.dynamic_route or page_data:
			context.no_cache = 1

		if frappe.flags.for_preview and self.draft_blocks:
			blocks = self.draft_blocks

		builder_variables = frappe.get_all("Builder Variable", fields=["variable_name", "value"])
		css_variables = {}
		for builder_variable in builder_variables:
			if builder_variable.variable_name and builder_variable.value:
				variable_name = f"--{camel_case_to_kebab_case(builder_variable.variable_name, True)}"
				css_variables[variable_name] = builder_variable.value
		context.css_variables = css_variables

		content, style, fonts = get_block_html(blocks)
		self.set_custom_font(context, fonts)
		context.fonts = fonts
		context.content = content
		context.style = render_template(style, page_data)
		context.editor_link = f"/{builder_path}/page/{self.name}"
		if frappe.form_dict and self.dynamic_route:
			query_string = "&".join(
				[
					f"{k}={frappe.utils.escape_html(frappe.utils.quote(v))}"
					for k, v in frappe.form_dict.items()
				]
			)
			context.editor_link += f"?{query_string}"

		context.page_name = self.name
		if frappe.flags.for_preview:
			if self.dynamic_route and hasattr(frappe.local, "request"):
				context.base_url = frappe.utils.get_url(frappe.local.request.path or self.route)
			else:
				context.base_url = frappe.utils.get_url(self.route)

		context.update(page_data)

		self.set_style_and_script(context)
		self.set_meta_tags(context=context, page_data=page_data)
		self.set_favicon(context)
		context.page_data = clean_data(context.page_data)
		try:
			context["content"] = render_template(context.content, context)
		except TemplateSyntaxError:
			raise

	def set_meta_tags(self, context, page_data=None):
		if not page_data:
			page_data = {}

		metatags = {
			"title": self.page_title or "My Page",
			"description": self.meta_description or self.page_title,
			"image": self.meta_image or self.preview,
		}
		metatags.update(page_data.get("metatags", {}))
		context.metatags = metatags

	def set_favicon(self, context):
		if not context.get("favicon"):
			context.favicon = self.favicon
		if not context.get("favicon"):
			context.favicon = frappe.get_cached_value("Builder Settings", None, "favicon")

	def is_component_used(self, component_id):
		if self.blocks and is_component_used(self.blocks, component_id):
			return True
		elif self.draft_blocks and is_component_used(self.draft_blocks, component_id):
			return True

	def set_style_and_script(self, context):
		for script in self.get("client_scripts", []):
			script_doc = frappe.get_cached_doc("Builder Client Script", script.builder_script)
			if script_doc.script_type == "JavaScript":
				context.setdefault("scripts", []).append(script_doc.public_url)
			else:
				context.setdefault("styles", []).append(script_doc.public_url)

		if not context.get("_head_html"):
			context._head_html = ""

		if not context.get("_body_html"):
			context._body_html = ""

		if self.head_html:
			context._head_html += self.head_html

		if self.body_html:
			context._body_html += self.body_html

		builder_settings = frappe.get_cached_doc("Builder Settings", "Builder Settings")
		if builder_settings.script:
			context.setdefault("scripts", []).append(builder_settings.script_public_url)
		if builder_settings.style:
			context.setdefault("styles", []).append(builder_settings.style_public_url)
		if builder_settings.head_html:
			context._head_html += builder_settings.head_html
		if builder_settings.body_html:
			context._body_html += builder_settings.body_html

		context["_head_html"] = render_template(context._head_html, context)
		context["_body_html"] = render_template(context._body_html, context)

	@frappe.whitelist()
	def get_page_data(self, route_variables=None):
		if route_variables:
			frappe.form_dict.update(frappe.parse_json(route_variables or "{}"))
		page_data = frappe._dict()
		if self.page_data_script:
			_locals = dict(data=frappe._dict())
			execute_script(self.page_data_script, _locals, self.name)
			page_data.update(_locals["data"])
		return page_data

	def generate_page_preview_image(self, html=None):
		public_path, local_path = get_builder_page_preview_file_paths(self)
		frappe.flags.for_preview = True
		generate_preview(
			html or get_response_content(self.route),
			local_path,
		)
		self.db_set("preview", public_path, commit=True, update_modified=False)

	def set_custom_font(self, context, font_map):
		user_fonts = frappe.get_all(
			"User Font", fields=["font_name", "font_file"], filters={"name": ("in", list(font_map.keys()))}
		)
		if user_fonts:
			context.custom_fonts = user_fonts
		for font in user_fonts:
			del font_map[font.font_name]

	def replace_component(self, target_component, replace_with):
		if self.blocks:
			blocks = frappe.parse_json(self.blocks)
			self.blocks = frappe.as_json(replace_component_in_blocks(blocks, target_component, replace_with))
			self.db_set("blocks", self.blocks, commit=True, update_modified=False)
		if self.draft_blocks:
			draft_blocks = frappe.parse_json(self.draft_blocks)
			self.draft_blocks = frappe.as_json(
				replace_component_in_blocks(draft_blocks, target_component, replace_with)
			)
			self.db_set("draft_blocks", self.draft_blocks, commit=True, update_modified=False)

		self.clear_route_cache()

	def is_home_page(self):
		"""Check if this page is set as the home page in Builder Settings."""
		return frappe.get_cached_value("Builder Settings", None, "home_page") == self.route


def replace_component_in_blocks(blocks, target_component, replace_with):
	for target_block in blocks:
		if target_block.get("extendedFromComponent") == target_component:
			new_component_block = frappe.parse_json(
				frappe.get_cached_value("Builder Component", replace_with, "block")
			)
			target_block.clear()
			target_block.update(new_component_block)
			target_block["extendedFromComponent"] = replace_with
			reset_with_component(target_block, replace_with, new_component_block.get("children"))
		else:
			target_block["children"] = replace_component_in_blocks(
				target_block.get("children", []) or [], target_component, replace_with
			)

	return blocks


def save_as_template(page_doc: BuilderPage):
	# move all assets to www/builder_assets/{page_name}
	if page_doc.draft_blocks:
		page_doc.publish()
	if not page_doc.template_name:
		page_doc.template_name = page_doc.page_title

	blocks = frappe.parse_json(page_doc.blocks)
	for block in blocks:
		copy_img_to_asset_folder(block, page_doc)

	page_doc.db_set("draft_blocks", None)
	page_doc.db_set("blocks", frappe.as_json(blocks, indent=None))
	page_doc.reload()
	export_to_files(
		record_list=[["Builder Page", page_doc.name, "builder_page_template"]], record_module="builder"
	)

	components = set()

	def get_component(block):
		if block.get("extendedFromComponent"):
			component = block.get("extendedFromComponent")
			components.add(component)
			# export nested components as well
			component_doc = frappe.get_cached_doc("Builder Component", component)
			if component_doc.block:
				component_block = frappe.parse_json(component_doc.block)
				get_component(component_block)
		for child in block.get("children", []) or []:
			get_component(child)

	for block in blocks:
		get_component(block)

	if components:
		export_to_files(
			record_list=[["Builder Component", c, "builder_component"] for c in components],
			record_module="builder",
		)

	scripts = frappe.get_all(
		"Builder Page Client Script",
		filters={"parent": page_doc.name},
		fields=["name", "builder_script"],
	)
	if scripts:
		export_to_files(
			record_list=[
				["Builder Client Script", s.builder_script, "builder_client_script"] for s in scripts
			],
			record_module="builder",
		)


def get_block_html(blocks):
	blocks = frappe.parse_json(blocks)
	if not isinstance(blocks, list):
		blocks = [blocks]
	soup = bs.BeautifulSoup("", "html.parser")
	style_tag = soup.new_tag("style")
	font_map = {}

	def get_html(blocks, soup):
		html = ""

		def get_tag(block, soup, data_key=None):
			block = extend_with_component(block)
			set_dynamic_content_placeholder(block, data_key)
			element = block.get("originalElement") or block.get("element")

			if not element:
				return ""

			classes = block.get("classes", [])
			if element in (
				"span",
				"h1",
				"p",
				"b",
				"h2",
				"h3",
				"h4",
				"h5",
				"h6",
				"label",
				"a",
			):
				classes.insert(0, "__text_block__")

			# temp fix: since p inside p is illegal
			if element in ["p", "__raw_html__"]:
				element = "div"

			tag = soup.new_tag(element)
			tag.attrs = block.get("attributes", {})

			customAttributes = block.get("customAttributes", {})
			if customAttributes:
				for key, value in customAttributes.items():
					tag[key] = value

			if block.get("baseStyles", {}):
				style_class = f"fb-{frappe.generate_hash(length=8)}"
				styles = {
					"base": split_styles(block.get("baseStyles", {})),
					"mobile": split_styles(block.get("mobileStyles", {})),
					"tablet": split_styles(block.get("tabletStyles", {})),
					"raw": split_styles(block.get("rawStyles", {})),
				}

				set_fonts(
					[
						styles["base"]["regular"],
						styles["mobile"]["regular"],
						styles["tablet"]["regular"],
						styles["raw"]["regular"],
					],
					font_map,
				)

				append_style(styles["base"]["regular"], style_tag, style_class)
				append_style(styles["raw"]["regular"], style_tag, style_class)
				append_state_style(styles["raw"]["state"], style_tag, style_class)
				append_state_style(styles["base"]["state"], style_tag, style_class)

				append_style(styles["tablet"]["regular"], style_tag, style_class, device="tablet")
				append_state_style(styles["tablet"]["state"], style_tag, style_class, device="tablet")

				append_style(styles["mobile"]["regular"], style_tag, style_class, device="mobile")
				append_state_style(styles["mobile"]["state"], style_tag, style_class, device="mobile")

				classes.insert(0, style_class)

			tag.attrs["class"] = " ".join(classes)

			innerContent = block.get("innerHTML")
			if innerContent:
				inner_soup = bs.BeautifulSoup(innerContent, "html.parser")
				set_fonts_from_html(inner_soup, font_map)
				tag.append(inner_soup)

			if block.get("isRepeaterBlock") and block.get("children") and block.get("dataKey"):
				_key = block.get("dataKey").get("key")
				if data_key:
					_key = f"{data_key}.{_key}"

				item_key = f"key_{_key.replace('.', '__')}"
				tag.append(f"{{% for {item_key} in {_key} %}}")
				tag.append(get_tag(block.get("children")[0], soup, item_key))
				tag.append("{% endfor %}")
			else:
				for child in block.get("children", []) or []:
					if child.get("visibilityCondition"):
						key = child.get("visibilityCondition")
						if data_key:
							key = f"{data_key}.{key}"
						tag.append(f"{{% if {key} %}}")
					tag.append(get_tag(child, soup, data_key=data_key))
					if child.get("visibilityCondition"):
						tag.append("{% endif %}")

			if element == "body":
				tag.append("{% include 'templates/generators/webpage_scripts.html' %}")

			return tag

		for block in blocks:
			html += str(get_tag(block, soup))

		return html, str(style_tag), font_map

	data = get_html(blocks, soup)
	return data


def get_style(style_obj):
	return (
		"".join(
			f"{camel_case_to_kebab_case(key)}: {value};"
			for key, value in style_obj.items()
			if value is not None and value != "" and not key.startswith("__")
		)
		if style_obj
		else ""
	)


def wrap_with_media_query(style_string, device):
	if device == "mobile":
		return f"@media only screen and (max-width: {MOBILE_BREAKPOINT}px) {{ {style_string} }}"
	elif device == "tablet":
		return f"@media only screen and (max-width: {DESKTOP_BREAKPOINT - 1}px) {{ {style_string} }}"
	return style_string


def append_style(style_obj, style_tag, style_class, device="desktop"):
	style = get_style(style_obj)
	if not style:
		return
	style_string = f".{style_class} {{ {style} }}"
	style_tag.append(wrap_with_media_query(style_string, device))


def append_state_style(style_obj, style_tag, style_class, device="desktop"):
	for key, value in style_obj.items():
		if ":" in key:
			state, property = key.split(":", 1)
			css_property = camel_case_to_kebab_case(property)
			style_string = f".{style_class}:{state} {{ {css_property}: {value}; }}"
			style_tag.append(wrap_with_media_query(style_string, device))


def set_fonts(styles, font_map):
	for style in styles:
		font = style.get("fontFamily")
		if font:
			# escape spaces in font name
			style["fontFamily"] = font.replace(" ", "\\ ")
			if font in font_map:
				if style.get("fontWeight") and style.get("fontWeight") not in font_map[font]["weights"]:
					font_map[font]["weights"].append(style.get("fontWeight"))
					font_map[font]["weights"].sort()
			else:
				font_map[font] = {"weights": [style.get("fontWeight") or "400"]}


def set_fonts_from_html(soup, font_map):
	# get font-family from inline styles
	for tag in soup.find_all(style=True):
		styles = tag.attrs.get("style").split(";")
		for style in styles:
			if "font-family" in style:
				font = style.split(":")[1].strip()
				if font:
					font_map[font] = {"weights": ["400"]}


def extend_with_component(block):
	if block.get("extendedFromComponent"):
		component = frappe.get_cached_value(
			"Builder Component",
			block["extendedFromComponent"],
			["block", "name"],
			as_dict=True,
		)
		component_block = frappe.parse_json(component.block if component else "{}")
		if component_block:
			extend_block(component_block, block)
			block = component_block

	return block


def extend_block(block, overridden_block):
	block["baseStyles"].update(overridden_block["baseStyles"])
	block["mobileStyles"].update(overridden_block["mobileStyles"])
	block["tabletStyles"].update(overridden_block["tabletStyles"])
	block["attributes"].update(overridden_block["attributes"])
	block["dynamicValues"] = block.get("dynamicValues", []) + overridden_block.get("dynamicValues", [])
	if overridden_block.get("element"):
		block["element"] = overridden_block["element"]

	if overridden_block.get("visibilityCondition"):
		block["visibilityCondition"] = overridden_block.get("visibilityCondition")

	if not block.get("customAttributes"):
		block["customAttributes"] = {}
	block["customAttributes"].update(overridden_block.get("customAttributes", {}))

	if not block.get("rawStyles"):
		block["rawStyles"] = {}
	block["rawStyles"].update(overridden_block.get("rawStyles", {}))

	block["classes"].extend(overridden_block["classes"])
	dataKey = overridden_block.get("dataKey", {})
	if not block.get("dataKey"):
		block["dataKey"] = {}
	if dataKey:
		block["dataKey"].update({k: v for k, v in dataKey.items() if v is not None})
	if overridden_block.get("innerHTML"):
		block["innerHTML"] = overridden_block["innerHTML"]
	component_children = block.get("children", []) or []
	overridden_children = overridden_block.get("children", []) or []
	extended_children = []
	for overridden_child in overridden_children:
		component_child = next(
			(
				child
				for child in component_children
				if child.get("blockId")
				in [
					overridden_child.get("blockId"),
					overridden_child.get("referenceBlockId"),
				]
			),
			None,
		)
		if component_child:
			extended_children.append(extend_block(copy.deepcopy(component_child), overridden_child))
		else:
			extended_children.append(overridden_child)
	block["children"] = extended_children
	return block


def set_dynamic_content_placeholder(block, data_key=False):
	block_data_key = block.get("dataKey", {}) or {}
	dynamic_values = [block_data_key] if block_data_key else []
	dynamic_values += block.get("dynamicValues", []) or []
	for dynamic_value_doc in dynamic_values:
		if not isinstance(dynamic_value_doc, dict):
			# if dynamic_value_doc is a string, convert it to dict
			dynamic_value_doc = {"key": dynamic_value_doc, "type": "key", "property": dynamic_value_doc}
		if dynamic_value_doc and dynamic_value_doc.get("key"):
			key = f"{data_key}.{dynamic_value_doc.get('key')}" if data_key else dynamic_value_doc.get("key")
			if data_key:
				# convert a.b to (a or {}).get('b', {})
				# to avoid undefined error in jinja
				keys = key.split(".")
				key = f"({keys[0]} or {{}})"
				for k in keys[1:]:
					key = f"{key}.get('{k}', {{}})"

			_property = dynamic_value_doc.get("property")
			_type = dynamic_value_doc.get("type")
			if _type == "attribute":
				block["attributes"][_property] = (
					f"{{{{ {key} or '{escape_single_quotes(block['attributes'].get(_property, ''))}' }}}}"
				)
			elif _type == "style":
				if not block["attributes"].get("style"):
					block["attributes"]["style"] = ""
				css_property = camel_case_to_kebab_case(_property)
				block["attributes"]["style"] += (
					f"{css_property}: {{{{ {key} or '{escape_single_quotes(block['baseStyles'].get(_property, '') or '')}' }}}};"
				)
			elif _type == "key" and not block.get("isRepeaterBlock"):
				block[_property] = (
					f"{{{{ {key} if {key} or {key} in ['', 0] else '{escape_single_quotes(block.get(_property, ''))}' }}}}"
				)


@redis_cache(ttl=60 * 60)
def find_page_with_path(route):
	try:
		return frappe.db.get_value("Builder Page", dict(route=route, published=1), "name", cache=True)
	except frappe.DoesNotExistError:
		pass


@redis_cache(ttl=60 * 60)
def get_web_pages_with_dynamic_routes() -> dict[str, str]:
	return frappe.get_all(
		"Builder Page",
		fields=["name", "route", "modified"],
		filters=dict(published=1, dynamic_route=1),
		update={"doctype": "Builder Page"},
	)


def resolve_path(path):
	try:
		if find_page_with_path(path):
			return path
		elif evaluate_dynamic_routes(
			[ColonRule(f"/{d.route}", endpoint=d.name) for d in get_web_pages_with_dynamic_routes()],
			path,
		):
			return path
	except Exception:
		pass

	return original_resolve_path(path)


def reset_with_component(block, extended_with_component, component_children):
	reset_block(block)
	block["children"] = []
	for component_child in component_children:
		component_child_id = component_child.get("blockId")
		child_block = reset_block(component_child)
		child_block["isChildOfComponent"] = extended_with_component
		child_block["referenceBlockId"] = component_child_id
		block["children"].append(child_block)
		if child_block.get("extendedFromComponent"):
			component = frappe.get_cached_doc("Builder Component", child_block.get("extendedFromComponent"))
			component_block = frappe.parse_json(component.block)
			reset_with_component(
				child_block, child_block.get("extendedFromComponent"), component_block.get("children")
			)
		else:
			reset_with_component(child_block, extended_with_component, child_block.get("children"))


def reset_block(block):
	block["blockId"] = frappe.generate_hash(length=8)
	block["innerHTML"] = None
	block["element"] = None
	block["baseStyles"] = {}
	block["rawStyles"] = {}
	block["mobileStyles"] = {}
	block["tabletStyles"] = {}
	block["attributes"] = {}
	block["customAttributes"] = {}
	block["classes"] = []
	block["dataKey"] = {}
	return block
