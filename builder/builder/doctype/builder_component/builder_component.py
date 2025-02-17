# Copyright (c) 2023, asdf and contributors
# For license information, please see license.txt

import copy
import json
import os
from dataclasses import dataclass
from typing import Union

import frappe
from frappe.model.document import Document
from frappe.modules.export_file import export_to_files
from frappe.website.utils import clear_website_cache


class BuilderComponent(Document):
	def before_insert(self):
		if not self.component_id:
			self.component_id = frappe.generate_hash(length=16)

	def on_update(self):
		self.queue_action("clear_page_cache")
		print("on update")
		self.sync_component()
		self.update_exported_component()

	def clear_page_cache(self):
		pages = frappe.get_all("Builder Page", filters={"published": 1}, fields=["name"])
		for page in pages:
			page_doc = frappe.get_cached_doc("Builder Page", page.name)
			if page_doc.is_component_used(self.component_id):
				clear_website_cache(page_doc.route)

	def sync_component(self):
		pages = frappe.get_all("Builder Page", filters={"published": 1}, fields=["name"])
		for page in pages:
			page_doc = frappe.get_cached_doc("Builder Page", page.name)
			print("checking page", page_doc.name, page_doc.is_component_used(self.component_id))
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


@dataclass
class BlockDataKey:
	key: str
	property: str
	type: str


@dataclass
class Block:
	blockId: str
	children: list["Block"]
	baseStyles: dict
	rawStyles: dict
	mobileStyles: dict
	tabletStyles: dict
	attributes: dict
	classes: list[str]
	dataKey: BlockDataKey | None = None
	blockName: str | None = None
	element: str | None = None
	draggable: bool = False
	innerText: str | None = None
	innerHTML: str | None = None
	extendedFromComponent: str | None = None
	originalElement: str | None = None
	isChildOfComponent: str | None = None
	referenceBlockId: str | None = None
	isRepeaterBlock: bool = False
	visibilityCondition: str | None = None
	elementBeforeConversion: str | None = None
	customAttributes: dict | None = None

	def __init__(self, **kwargs) -> None:
		for key, value in kwargs.items():
			if key == "children":
				value = [Block(**b) if b and isinstance(b, dict) else None for b in (value or [])]
			setattr(self, key, value)

	def as_dict(self):
		return {
			"blockId": self.blockId,
			"children": [child.as_dict() for child in self.children] if self.children else None,
			"baseStyles": self.baseStyles,
			"rawStyles": self.rawStyles,
			"mobileStyles": self.mobileStyles,
			"tabletStyles": self.tabletStyles,
			"attributes": self.attributes,
			"classes": self.classes,
			"dataKey": self.dataKey.__dict__ if self.dataKey else None,
			"blockName": self.blockName,
			"element": self.element,
			"draggable": self.draggable,
			"innerText": self.innerText,
			"innerHTML": self.innerHTML,
			"extendedFromComponent": self.extendedFromComponent,
			"originalElement": self.originalElement,
			"isChildOfComponent": self.isChildOfComponent,
			"referenceBlockId": self.referenceBlockId,
			"isRepeaterBlock": self.isRepeaterBlock,
			"visibilityCondition": self.visibilityCondition,
			"elementBeforeConversion": self.elementBeforeConversion,
			"customAttributes": self.customAttributes,
		}


class ComponentSyncer:
	def __init__(self, page_doc) -> None:
		self._page_doc = page_doc

	def sync_component(self, component) -> None:
		"""Sync a component across draft and published blocks"""
		if self._page_doc.draft_blocks:
			self._page_doc.draft_blocks = self._sync_blocks(self._page_doc.draft_blocks, component)
		if self._page_doc.blocks:
			self._page_doc.blocks = self._sync_blocks(self._page_doc.blocks, component)
		self._page_doc.save()

	def _sync_blocks(self, blocks: str | list[Block], component) -> str:
		"""Sync component changes in a blocks JSON string"""
		print("sync component instance")
		if isinstance(blocks, str):
			blocks_list = self._parse_blocks(blocks)
		else:
			blocks_list = blocks
		for block in blocks_list:
			if not block:
				continue
			if block.extendedFromComponent == component.component_id:
				component_block = Block(**frappe.parse_json(component.block))
				self._sync_single_block(block, block, component.name, component_block.children or [])
			else:
				self._sync_blocks(block.children or [], component)
		blocks_dict = [block.as_dict() for block in blocks_list]
		return frappe.as_json(blocks_dict)

	def _sync_single_block(
		self, parent: Block, block: Block, component_name: str, component_children: list[Block]
	) -> None:
		"""Sync a single block with its component template"""
		parent_children = parent.children or []

		# Add new blocks
		for index, component_child in enumerate(component_children):
			if not self._find_component_block(component_child.blockId, parent_children):
				block_component = self._create_component_block(component_child, component_name)
				if not block.children:
					block.children = []
				block.children.insert(index, block_component)

		# Sync existing blocks recursively
		for child in block.children or []:
			component_child = next(
				(c for c in component_children if c.blockId == child.referenceBlockId), None
			)
			if component_child:
				self._sync_single_block(parent, child, component_name, component_child.children or [])

	@staticmethod
	def _parse_blocks(blocks: str) -> list[Block]:
		"""Parse blocks JSON into Block objects"""
		blocks_list = frappe.parse_json(blocks)
		if not isinstance(blocks_list, list):
			blocks_list = [blocks_list]
		return [Block(**b) if b else b for b in blocks_list]

	@staticmethod
	def _find_component_block(block_id: str, children: list[Block]) -> Block | None:
		"""Find a component block by ID in children"""
		return next((c for c in children if c.referenceBlockId == block_id), None)

	@staticmethod
	def _create_component_block(component_child: Block, component_name: str) -> Block:
		"""Create a new block from component template"""
		print("creating new block")
		block = copy.deepcopy(component_child)
		block.blockId = frappe.generate_hash(length=8)
		block.isChildOfComponent = component_name
		block.referenceBlockId = component_child.blockId
		ComponentSyncer._reset_block_styles(block)
		return block

	@staticmethod
	def _reset_block_styles(block: Block) -> None:
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

		for child in block.children or []:
			if not child.extendedFromComponent:
				ComponentSyncer._reset_block_styles(child)
