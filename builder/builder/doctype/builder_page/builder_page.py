# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

import copy
import os
import re
import shutil

import bs4 as bs
import frappe
import frappe.utils
from frappe.modules import scrub
from frappe.modules.export_file import export_to_files
from frappe.utils import set_request
from frappe.utils.caching import redis_cache
from frappe.utils.jinja import render_template
from frappe.website.page_renderers.document_page import DocumentPage
from frappe.website.path_resolver import evaluate_dynamic_routes
from frappe.website.path_resolver import resolve_path as original_resolve_path
from frappe.website.serve import get_response_content
from frappe.website.utils import clear_cache
from frappe.website.website_generator import WebsiteGenerator
from jinja2.exceptions import TemplateSyntaxError

from builder.export_import_standard_page import export_page_as_standard
from builder.hooks import builder_path
from builder.html_preview_image import generate_preview
from builder.utils import (
	Block,
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
			context["canonical_url"] = frappe.utils.get_url()
		elif self.doc.canonical_url:
			context["canonical_url"] = render_template(self.doc.canonical_url, context)
		else:
			context["canonical_url"] = frappe.utils.get_url(self.path)
		self.context = context

	def set_missing_values(self):
		self.set_canonical_url()


class BuilderPage(WebsiteGenerator):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from builder.builder.doctype.builder_page_client_script.builder_page_client_script import (
			BuilderPageClientScript,
		)

		app: DF.Literal[None]
		authenticated_access: DF.Check
		blocks: DF.LongText | None
		body_html: DF.Code | None
		canonical_url: DF.Data | None
		client_scripts: DF.TableMultiSelect[BuilderPageClientScript]
		disable_indexing: DF.Check
		draft_blocks: DF.LongText | None
		dynamic_route: DF.Check
		favicon: DF.AttachImage | None
		head_html: DF.Code | None
		is_standard: DF.Check
		is_template: DF.Check
		language: DF.Data | None
		meta_description: DF.SmallText | None
		meta_image: DF.AttachImage | None
		page_data_script: DF.Code | None
		page_name: DF.Data | None
		page_title: DF.Data | None
		preview: DF.Data | None
		project_folder: DF.Link | None
		published: DF.Check
		route: DF.Data | None
	# end: auto-generated types

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
				setattr(self, block_type, frappe.as_json(getattr(self, block_type), indent=0))
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
			if self.route and (":" in self.route or "<" in self.route):
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
			if frappe.get_cached_value("Builder Settings", "Builder Settings", "home_page") == self.route:
				frappe.db.set_value("Builder Settings", "Builder Settings", "home_page", None)

		if frappe.conf.developer_mode and self.is_template:
			save_as_template(self)

		if frappe.conf.developer_mode and self.is_standard and self.app:
			export_page_as_standard(self.name, target_app=self.app)

	def clear_route_cache(self):
		get_web_pages_with_dynamic_routes.clear_cache()
		find_page_with_path.clear_cache()
		clear_cache(self.route)

	def on_trash(self):
		if self.is_template and frappe.conf.developer_mode:
			page_template_folder = os.path.join(
				frappe.get_app_path("builder"), "builder", "builder_page_template", scrub(str(self.name))
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
			for k, v in frappe.parse_json(route_variables or "{}").items():
				frappe.form_dict[k] = v
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
		
		# TODO: detect dynamic_route or block/page data
		context.no_cache = 1

		context.preview = getattr(getattr(frappe.local, "request", None), "for_preview", None)

		if context.preview and self.draft_blocks:
			blocks = self.draft_blocks

		content, style, fonts = get_block_html(blocks)
		self.set_custom_font(context, fonts)
		context.fonts = fonts
		context.__content = content
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
		if context.preview:
			if self.dynamic_route and hasattr(frappe.local, "request"):
				context.base_url = frappe.utils.get_url(frappe.local.request.path or self.route)
			else:
				context.base_url = frappe.utils.get_url(self.route)

		context.update(page_data)

		self.set_style_and_script(context)
		self.set_meta_tags(context=context, page_data=page_data)
		self.set_favicon(context)
		self.set_language(context)
		context.page_data = clean_data(context.page_data)
		try:
			context["__content"] = render_template(context.__content, context)
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
			context.favicon = frappe.get_cached_value("Builder Settings", "Builder Settings", "favicon")

	def set_language(self, context):
		# Set page-specific language or fall back to default language from Builder Settings
		context.language = self.language
		if not context.language:
			context.default_language = (
				frappe.get_cached_value("Builder Settings", "Builder Settings", "default_language") or "en"
			)

	def is_component_used(self, component_id):
		if self.blocks and is_component_used(self.blocks, component_id):
			return True
		elif self.draft_blocks and is_component_used(self.draft_blocks, component_id):
			return True

	def set_style_and_script(self, context):
		builder_settings = frappe.get_cached_doc("Builder Settings", "Builder Settings")
		if builder_settings.script:
			context.setdefault("scripts", []).append(builder_settings.script_public_url)
		if builder_settings.style:
			context.setdefault("styles", []).append(builder_settings.style_public_url)

		client_scripts = self.get("client_scripts") or []
		for script in client_scripts:
			script_doc = frappe.get_cached_doc("Builder Client Script", script.builder_script)
			if script_doc.script_type == "JavaScript":
				context.setdefault("scripts", []).append(script_doc.public_url)
			else:
				context.setdefault("styles", []).append(script_doc.public_url)

		if not context.get("_head_html"):
			context._head_html = ""

		if not context.get("_body_html"):
			context._body_html = ""

		if builder_settings.head_html:
			context._head_html += builder_settings.head_html
		if builder_settings.body_html:
			context._body_html += builder_settings.body_html

		if self.head_html:
			context._head_html += self.head_html
		if self.body_html:
			context._body_html += self.body_html

		context["_head_html"] = render_template(context._head_html, context)
		context["_body_html"] = render_template(context._body_html, context)

	@frappe.whitelist()
	def get_page_data(self, route_variables=None):
		if route_variables:
			frappe.form_dict.update(dict(frappe.parse_json(route_variables or "{}").items()))
		page_data = frappe._dict()
		if self.page_data_script:
			_locals = dict(data=frappe._dict(), page=frappe._dict())
			execute_script(self.page_data_script, _locals, self.name)
			page_data.update(_locals["data"])
			page_data.update(_locals["page"])

		# do not let users replace __content
		page_data.pop("__content", None)

		return page_data

	def generate_page_preview_image(self, html=None):
		public_path, local_path = get_builder_page_preview_file_paths(self)
		if not html:
			set_request(method="GET", path=self.route)
			frappe.local.request.for_preview = True
			html = get_response_content()

		generate_preview(
			html,
			local_path,
		)
		self.db_set("preview", public_path, commit=True, update_modified=False)

	def set_custom_font(self, context, font_map):
		user_fonts = frappe.get_all(
			"User Font",
			fields=["font_name", "font_file"],
			filters={"font_name": ("in", list(font_map.keys()))},
		)
		if user_fonts:
			context.custom_fonts = user_fonts
		for font in user_fonts:
			font_map.pop(font.font_name, None)

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
		return frappe.get_cached_value("Builder Settings", "Builder Settings", "home_page") == self.route


def replace_component_in_blocks(blocks, target_component, replace_with) -> list[dict]:
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

	blocks: list[Block] = frappe.parse_json(page_doc.blocks or "[]")  # type: ignore
	for block in blocks:
		copy_img_to_asset_folder(block, page_doc)

	page_doc.db_set("draft_blocks", None)
	page_doc.db_set("blocks", frappe.as_json(blocks, indent=0))
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


@frappe.whitelist()
def get_block_data(block_id, block_data_script, props):
	props = frappe._dict(frappe.parse_json(props or "{}"))
	block_data = frappe._dict()
	_locals = dict(block=frappe._dict(), props=props)
	execute_script(block_data_script, _locals, block_id)
	block_data.update(_locals["block"])
	return block_data

def get_block_html(blocks):
	blocks = frappe.parse_json(blocks)
	if not isinstance(blocks, list):
		blocks = [blocks]
	soup = bs.BeautifulSoup("", "html.parser")
	style_tag = soup.new_tag("style")
	font_map = {}

	def get_html(blocks, soup):

		map_of_std_props_info = {} # prop_name -> list of prop_info stack
		html = ""

		def get_tag(block, soup, data_key=None):
			block = extend_with_component(block)

			props_obj = {}

			if block.get("props"):
				for prop_name, prop_info in block.get("props").items():
					is_standard = prop_info.get("isStandard", False)
					is_passed_down = prop_info.get("isPassedDown", False)
					interpreted_value = get_interpreted_prop_value(prop_info, data_key)

					if is_standard:
						map_of_std_props_info.setdefault(prop_name, []).append(prop_info)
					
					props_obj[prop_name] = {"value": interpreted_value, "is_standard": is_standard, "is_passed_down": is_passed_down}

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
				comes_from = block.get("dataKey").get("comesFrom", "dataScript")
				default_props = None

				loop_var, iterator_key, data_key = get_iterator_info(block, data_key, map_of_std_props_info)

				tag.append(f"{{% for {loop_var} in {iterator_key} %}}")

				child_tag, child_tag_details = get_tag(block.get("children")[0], soup, data_key)
				
				if comes_from == "props":
					default_props = get_loop_vars(map_of_std_props_info, block.get("dataKey").get("key"))
					child_tag_details['default_props'] = default_props

				append_child_tag(tag, child_tag, child_tag_details)
     
				tag.append("{% endfor %}")
			else:
				for child in block.get("children", []) or []:
					visibility_key = get_visibility_key(child, data_key)
					child_tag, child_tag_details = get_tag(child, soup, data_key=data_key)
					child_tag_details['visibility_key'] = visibility_key
					append_child_tag(tag, child_tag, child_tag_details)

			if element == "body":
				tag.append("{% include 'templates/generators/webpage_scripts.html' %}")

			for prop_name, prop_info in props_obj.items():
				if prop_info.get("is_standard"):
					map_of_std_props_info[prop_name].pop()

			all_props = {k: v["value"] for k, v in props_obj.items()}
			passed_down_props = {k: v["value"] for k, v in props_obj.items() if v.get("is_passed_down")}

			if block.get("blockClientScript"):
				script_content = f"(function (props){{ {block.get('blockClientScript')} }}).call(document.querySelector('[data-block-id=\"{{{{ unique_hash }}}}\"]'), {{{{ props | to_safe_json }}}});"
				tag.attrs["data-block-id"] = f"{{{{ unique_hash }}}}" # unique hash as repeating blocks have same blockId / class
				script_tag = soup.new_tag("script")
				script_tag.string = script_content
				tag.append(script_tag)
			
			tag_details = {
				"all_props": to_jinja_literal(all_props),
				"passed_down_props": to_jinja_literal(passed_down_props),
				"block_data_script": block.get("blockDataScript", None),
			}

			return tag, tag_details

		for block in blocks:
			tag, tag_details = get_tag(block, soup)

			html += f"{{% with block = {{ }} | execute_script_and_combine('{escape_single_quotes(tag_details.get('block_data_script', ''))}', {(tag_details.get('all_props', '{}'))}) %}}{tag!s}{{% endwith %}}"
			html = f"{{% with props = {tag_details.get('all_props', '{}')} %}}{html}{{% endwith %}}"
			html = f"{{% with passed_down_props = {tag_details.get('passed_down_props', '{}')} %}}{html}{{% endwith %}}"
			
		# print("Final HTML: ", html)
		# write to file
		with open("output.html", "w") as f:
			f.write(html)
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

def get_interpreted_prop_value(prop, data_key):
	prop_is_dynamic = prop.get("isDynamic", False)
	prop_comes_from = prop.get("comesFrom", "props")
	prop_is_standard = prop.get("isStandard", False)
	prop_value = prop.get("value")
	
	default_value = prop.get("standardOptions", {}).get("options", {}).get("defaultValue") if prop_is_standard else None
	
	if prop_value is None:
		return default_value if prop_is_standard else "undefined"
	
	if prop_is_dynamic:
		key_mapping = {
			"dataScript": jinja_safe_key(f"{extract_data_key(data_key)}.{prop_value}") if data_key else prop_value,
			"blockDataScript": jinja_safe_key(f"block.{prop_value}"),
			"props": jinja_safe_key(f"props.{prop_value}")
		}
		key = key_mapping.get(prop_comes_from, prop_value)
		fallback = escape_single_quotes(default_value) if default_value is not None else 'undefined'
		return f"{{{{ {key} if {key} is defined else '{fallback}' }}}}"
	
	if prop_is_standard:
		prop_value = parse_static_value(
			prop_value or default_value,
			prop.get("standardOptions", {}).get("type"),
		)
	
	return prop_value if prop_value is not None else "undefined"

def get_iterator_info(block, data_key, map_of_std_props_info):
	iterator_key = block.get("dataKey").get("key")
	loop_var = ""
	comes_from = block.get("dataKey").get("comesFrom", "dataScript")

	if comes_from == "props":
		loop_vars = get_loop_vars(map_of_std_props_info, iterator_key)

		loop_var = ", ".join(loop_vars)  # `item` for array and `key, value` for object
		iterator_key = jinja_safe_key(f"props.{iterator_key}")

		if len(loop_vars) > 1:  # object repeater
			iterator_key = f"{iterator_key}.items()"

	elif comes_from == "blockDataScript":		
		# resetting block_data for repeater blocks by reassigning loop_var to "block"
		loop_var = "block"
		iterator_key = jinja_safe_key(f"block.{iterator_key}")
	else:
		if data_key:
			iterator_key = f"{extract_data_key(data_key)}.{iterator_key}"
		loop_var = f"key_{iterator_key.replace('.', '__')}"
		iterator_key = jinja_safe_key(iterator_key)
		data_key = {"key": loop_var, "comesFrom": "dataScript"}
	return loop_var, iterator_key, data_key

def get_visibility_key(block, data_key):
	if block.get("visibilityCondition"):
		visibility_condition = block.get("visibilityCondition")
		if isinstance(visibility_condition, str) or visibility_condition.get("comesFrom", "dataScript") == "dataScript":
			if data_key:
				visibility_key = f"{extract_data_key(data_key)}.{key}"
			else:
				visibility_key = visibility_condition.get("key")
		else:
			key = visibility_condition.get("key")
			if visibility_condition.get("comesFrom") == "props":
				visibility_key = f"props.{key}"
			else:
				visibility_key = f"block.{key}"
			visibility_key = jinja_safe_key(visibility_key)
		return visibility_key
	return None

def get_loop_vars(map_of_std_props_info, key):
	if key in map_of_std_props_info:
		std_prop_info = map_of_std_props_info[key][-1]
		standard_options = std_prop_info.get("standardOptions", {})
		if standard_options.get("type") == "array":
			return ["item"]  # TODO: allow custom item name
		elif standard_options.get("type") == "object":
			return ["key", "value"]  # TODO: allow custom key, value names
	return []

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

	dynamicValues = overridden_block.get("dynamicValues", [])
	dynamicValuesProperties = [dv.get("property") for dv in dynamicValues]
	for dv in block.get("dynamicValues", []):
		if dv.get("property") in dynamicValuesProperties:
			continue
		dynamicValues.append(dv)
	block["dynamicValues"] = dynamicValues

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

	if not block.get("props"):
		block["props"] = {}
	block["props"].update(overridden_block.get("props", {}))

	if overridden_block.get("blockClientScript"):
		block["blockClientScript"] = overridden_block.get("blockClientScript")

	if overridden_block.get("blockDataScript"):
		block["blockDataScript"] = overridden_block.get("blockDataScript")

	dataKey = overridden_block.get("dataKey", {})
	if not block.get("dataKey"):
		block["dataKey"] = {}
	if dataKey:
		block["dataKey"].update({k: v for k, v in dataKey.items() if v is not None and v != ""})
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


def append_child_tag(tag, child_tag, child_tag_details):
	
	child_tag_props = child_tag_details.get('all_props')
	child_passed_down_props = child_tag_details.get('passed_down_props')
	child_tag_block_script = child_tag_details.get('block_data_script')
	visibility_key = child_tag_details.get('visibility_key')
	default_props = child_tag_details.get('default_props')
 
	tag.append("{% with unique_hash = (loop.index if loop is defined else 0) | hash %}")

	if default_props:
		default_props = ", ".join([f"'{var}': {var}" for var in default_props])
		tag.append(f"{{% with passed_down_props = passed_down_props | combine({{ {default_props} }}) %}}")
		tag.append("{% with props = passed_down_props %}") # resetting props for repeater blocks and for props deriving from repeater loop vars

	tag.append(f"{{% with props = {child_tag_props} | combine(passed_down_props) %}}")
	tag.append(f"{{% with passed_down_props = passed_down_props | combine({child_passed_down_props}) %}}")
	
	if child_tag_block_script:
		tag.append(f"{{% with block = block | execute_script_and_combine('{escape_single_quotes(child_tag_block_script)}', props) %}}")
	
	if visibility_key:
		tag.append(f"{{% if {visibility_key} %}}")
	
	tag.append(child_tag)
	
	if visibility_key:
		tag.append("{% endif %}")
  
	if child_tag_block_script:
		tag.append("{% endwith %}")

	tag.append("{% endwith %}")
	tag.append("{% endwith %}")

	if default_props:
		tag.append("{% endwith %}{% endwith %}")

	tag.append("{% endwith %}")


def set_dynamic_content_placeholder(block, data_key=None):
	block_data_key = block.get("dataKey", {}) or {}
	dynamic_values = [block_data_key] if block_data_key else []
	dynamic_values += block.get("dynamicValues", []) or []
	for dynamic_value_doc in dynamic_values:
		original_key = dynamic_value_doc.get("key", "")
		if not isinstance(dynamic_value_doc, dict):
			# if dynamic_value_doc is a string, convert it to dict
			dynamic_value_doc = {"key": dynamic_value_doc, "type": "key", "property": dynamic_value_doc}
		if dynamic_value_doc and dynamic_value_doc.get("key"):
			key = ""
			if dynamic_value_doc.get("comesFrom") == "props":
				key = jinja_safe_key(f"props.{original_key}")
			elif dynamic_value_doc.get("comesFrom") == "blockDataScript":
				key = jinja_safe_key(f"block.{original_key}")
			else:
				key = (
					f"{extract_data_key(data_key)}.{dynamic_value_doc.get('key')}" if data_key else dynamic_value_doc.get("key")
				)
				if data_key:
					key = jinja_safe_key(key)

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
def get_web_pages_with_dynamic_routes() -> list[BuilderPage]:
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
	block["props"] = {}
	block["blockClientScript"] = None
	block["blockDataScript"] = None
	block["dynamicValues"] = []
	return block

def extract_data_key(data_key):
	if isinstance(data_key, str):
		return data_key
	elif isinstance(data_key, dict):
		return data_key.get("key")
	return None

def jinja_safe_key(key):
    # convert a.b to (a or {}).get('b', {})
	# to avoid undefined error in jinja
	keys = (key or "").split(".")
	key = f"({keys[0]} or {{}})"
	for k in keys[1:]:
		key = f"{key}.get('{k}', {{}})"
	return key

def to_jinja_literal(obj):
	# detect Jinja expressions inside strings (e.g. "{{ sample }}")
	if isinstance(obj, str):
		stripped = obj.strip()
		if re.fullmatch(r"{{\s*.*?\s*}}", stripped):
			# remove the {{ }} so Jinja receives the variable
			inner = stripped[2:-2].strip()
			return inner  # returned unquoted
		return repr(obj)

	if obj is True:
		return "True"
	if obj is False:
		return "False"
	if obj is None:
		return "None"

	if isinstance(obj, dict):
		parts = []
		for k, v in obj.items():
			parts.append(f"{to_jinja_literal(k)}: {to_jinja_literal(v)}")
		return "{ " + ", ".join(parts) + " }"

	if isinstance(obj, list | tuple):
		return "[ " + ", ".join(str(to_jinja_literal(i)) for i in obj) + " ]"

	return repr(obj)

def parse_static_value(value: str, prop_type: str):
	match prop_type:
		case "string":
			return f"{value}"
		case "number":
			try:
				return float(value)
			except ValueError:
				return None
		case "boolean":
			if value is True or value is False:
				return value
			if value.lower() in ["true", "1"]:
				return True
			elif value.lower() in ["false", "0"]:
				return False
			else:
				return None
		case "array":
			try:
				return frappe.parse_json(value)
			except Exception:
				return None
		case "object":
			try:
				return frappe.parse_json(value)
			except Exception:
				return None
		case "select":
			return f"{value}"
		case _:
			return f"{value}"
