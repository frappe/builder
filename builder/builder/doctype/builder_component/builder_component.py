# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

import copy
import os

import frappe
from frappe.model.document import Document
from frappe.modules.export_file import export_to_files
from frappe.utils.telemetry import capture
from frappe.website.utils import clear_website_cache

from builder.builder.component_versions import ensure_component_version
from builder.utils import Block, compact_json, execute_script


class BuilderComponent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		block: DF.JSON | None
		component_props: DF.JSON | None
		component_css: DF.Code | None
		component_data_script: DF.Code | None
		component_id: DF.Data | None
		component_js: DF.Code | None
		component_name: DF.Data | None
		for_web_page: DF.Link | None
	# end: auto-generated types

	def before_insert(self):
		if not self.component_id:
			self.component_id = frappe.generate_hash(length=16)
		capture("builder_component_created", "builder")

	def validate(self):
		validate_component_slots(frappe.parse_json(self.block or "{}"))

	def on_update(self):
		# Skip the background cache-clear and version snapshot during bulk imports
		# (install / migrate / import_doc). queue_action enqueues a job AND locks the
		# doc, which can raise DocumentLockedError mid-import — e.g. when
		# create_page_from_template import_doc's a hub template's components.
		# ensure_component_version also walks nested components and prunes, which is
		# unsafe when not all components are loaded yet. Versions are minted on the
		# next real edit, so nothing is lost by skipping a fresh import.
		if not (
			frappe.flags.in_import
			or frappe.flags.in_install
			or frappe.flags.in_migrate
			or frappe.flags.in_patch
		):
			self.queue_action("clear_page_cache")
			ensure_component_version(self.name)
		self.update_exported_component()

	def clear_page_cache(self):
		pages = frappe.get_all("Builder Page", filters={"published": 1}, fields=["name"])
		for page in pages:
			page_doc = frappe.get_cached_doc("Builder Page", page.name)
			if page_doc.is_component_used(self.component_id):
				clear_website_cache(page_doc.route)

	def sync_component(self):
		# Only load pages whose blocks/draft_blocks mention this component; the
		# precise is_component_used() check still runs below. Mirrors the filter
		# used by Builder Settings.replace_component to avoid scanning every page.
		pages = frappe.get_all(
			"Builder Page",
			fields=["name"],
			or_filters={
				"blocks": ["like", f"%{self.component_id}%"],
				"draft_blocks": ["like", f"%{self.component_id}%"],
			},
		)
		for page in pages:
			page_doc = frappe.get_cached_doc("Builder Page", page.name)
			if page_doc.is_component_used(self.component_id):
				ComponentSyncer(page_doc).sync_component(self)

	def update_exported_component(self):
		if not frappe.conf.developer_mode:
			return
		component_path = os.path.join(
			frappe.get_app_path("builder"), "builder", "builder_component", self.name
		)
		if os.path.exists(component_path):
			export_to_files(
				record_list=[["Builder Component", self.name, "builder_component"]],
				record_module="builder",
			)


def validate_component_slots(block: dict) -> None:
	slot_names: set[str] = set()

	def visit(
		node: dict,
		inside_slot: bool = False,
		inside_repeater: bool = False,
		is_root: bool = False,
	) -> None:
		if not is_root and node.get("extendedFromComponent"):
			return
		raw_slot_name = node.get("slotName")
		if raw_slot_name is not None and (
			not isinstance(raw_slot_name, str)
			or not raw_slot_name.strip()
			or raw_slot_name != raw_slot_name.strip()
		):
			frappe.throw(frappe._("Component slot names must be non-empty and trimmed"))
		slot_name = raw_slot_name or ""
		is_slot = bool(slot_name)
		if is_slot:
			if node.get("element") not in ("div", "section"):
				frappe.throw(frappe._("Component slots must be container blocks"))
			if inside_slot:
				frappe.throw(frappe._("Component slots cannot be nested"))
			if inside_repeater or node.get("isRepeaterBlock"):
				frappe.throw(frappe._("Component slots cannot be placed inside collections"))
			if slot_name in slot_names:
				frappe.throw(
					frappe._("Component slot names must be unique. Duplicate slot: {0}").format(slot_name)
				)
			slot_names.add(slot_name)
			node["slotName"] = slot_name

		for child in node.get("children") or []:
			visit(
				child,
				inside_slot=inside_slot or is_slot,
				inside_repeater=inside_repeater or bool(node.get("isRepeaterBlock")),
			)

	if isinstance(block, dict):
		visit(block, is_root=True)


class ComponentSyncer:
	def __init__(self, page_doc) -> None:
		self.page_doc = page_doc

	def sync_component(self, component) -> None:
		"""Sync a component across draft and published blocks"""
		if self.page_doc.draft_blocks:
			self.page_doc.draft_blocks = self.sync_blocks(self.page_doc.draft_blocks, component)
		if self.page_doc.blocks:
			self.page_doc.blocks = self.sync_blocks(self.page_doc.blocks, component)
		self.page_doc.save()
		self.page_doc.clear_route_cache()

	def sync_blocks(self, blocks: str | list[Block], component) -> str:
		"""Sync component changes in a blocks JSON string"""
		if isinstance(blocks, str):
			blocks_list = self.parse_blocks(blocks)
		else:
			blocks_list = blocks
		for block in blocks_list:
			if not block:
				continue
			if block.extendedFromComponent == component.component_id:
				component_block = Block(**frappe.parse_json(component.block))
				self.sync_single_block(block, component.name, component_block)
			else:
				self.sync_blocks(block.children or [], component)
		blocks_dict = [block.as_dict() if isinstance(block, Block) else block for block in blocks_list]
		return compact_json(blocks_dict)

	def sync_single_block(
		self,
		target_block: Block,
		component_name: str,
		component_block: Block,
		filled_slots: dict[str, Block] | None = None,
	):
		"""Sync a single block with its component template"""
		if filled_slots is None:
			filled_slots = self.collect_filled_slots(target_block)
		target_block.slotName = component_block.slotName
		root_slot = filled_slots.get(component_block.slotName) if component_block.slotName else None
		if root_slot:
			target_block.slotFilled = True
			target_block.children = copy.deepcopy(root_slot.children or [])
			return
		target_block.slotFilled = False
		if component_block.slotName:
			target_block.children = self.create_detached_slot_content(component_block.children or [])
			target_block.slotFilled = bool(target_block.children)
			return
		target_children = target_block.children or []
		target_block.children = []
		for index, component_child in enumerate(component_block.children or []):
			block_component = self.find_component_block(component_child.blockId, target_children)
			if not block_component:
				block_component = self.create_component_block(component_child, component_name)
			block_component.slotName = component_child.slotName
			filled_slot = filled_slots.get(component_child.slotName) if component_child.slotName else None
			if filled_slot:
				block_component.slotFilled = True
				block_component.children = copy.deepcopy(filled_slot.children or [])
			else:
				block_component.slotFilled = False
				self.sync_single_block(block_component, component_name, component_child, filled_slots)
			target_block.children.insert(index, block_component)

	@staticmethod
	def collect_filled_slots(root: Block) -> dict[str, Block]:
		slots: dict[str, Block] = {}

		def visit(block: Block, is_root: bool = False) -> None:
			if not is_root and block.extendedFromComponent:
				return
			if block.slotName and block.slotFilled:
				slots[block.slotName] = block
				return
			for child in block.children or []:
				visit(child)

		visit(root, True)
		return slots

	@staticmethod
	def create_detached_slot_content(component_children: list[Block]) -> list[Block]:
		children = copy.deepcopy(component_children)

		def detach(block: Block, inside_nested_component: bool = False) -> None:
			block.blockId = frappe.generate_hash(length=8)
			if not inside_nested_component:
				block.isChildOfComponent = None
				block.referenceBlockId = None
				if not block.extendedFromComponent:
					block.componentVersion = None
			inside_nested_component = inside_nested_component or bool(block.extendedFromComponent)
			for child in block.children or []:
				detach(child, inside_nested_component)

		for child in children:
			detach(child)
		return children

	@staticmethod
	def parse_blocks(blocks: str) -> list[Block]:
		"""Parse blocks JSON into Block objects"""
		blocks_list = frappe.parse_json(blocks)
		if not isinstance(blocks_list, list):
			blocks_list = [blocks_list]
		return [Block(**b) if b else b for b in blocks_list]

	@staticmethod
	def find_component_block(block_id: str, children: list[Block]) -> Block | None:
		"""Find a component block by ID in children"""
		return next((c for c in children if c.referenceBlockId == block_id), None)

	@staticmethod
	def create_component_block(component_child: Block, component_name: str) -> Block:
		"""Create a new block from component template"""
		block = copy.deepcopy(component_child)
		block.blockId = frappe.generate_hash(length=8)
		block.isChildOfComponent = component_name
		block.referenceBlockId = component_child.blockId
		reset_block_styles(block)

		# Recursively create children
		for index, child in enumerate(block.children or []):
			block.children[index] = ComponentSyncer.create_component_block(child, component_name)

		return block


def reset_block_styles(block: Block) -> None:
	"""Reset block styles to defaults"""
	block.innerHTML = None
	block.element = None
	block.baseStyles = dict()
	block.rawStyles = dict()
	block.mobileStyles = dict()
	block.tabletStyles = dict()
	block.attributes = dict()
	block.customAttributes = dict()
	block.classes = []
	block.children = block.children or []


def get_component_data(
	component_name: str, props: dict | str | None = None, script: str | None = None
) -> dict:
	"""Execute a component's data script with the given props and return the data dict.

	Args:
		component_name: The name/ID of the Builder Component
		props: Provided props or Component Props to pass to data script
		script: Provided data script or Component Data Script to execute

	Returns:
		A dict containing the component's data
	"""

	try:
		component_doc = frappe.get_cached_doc("Builder Component", component_name)
	except frappe.DoesNotExistError:
		return {}

	if script is None:
		script = component_doc.component_data_script
	props = props or component_doc.component_props

	if isinstance(props, str):
		props = frappe.parse_json(props)

	if not script:
		return {}

	_locals = dict(
		component=frappe._dict(),
		props=frappe._dict(props or {}),
	)

	execute_script(script, _locals, component_name)

	return _locals["component"]
