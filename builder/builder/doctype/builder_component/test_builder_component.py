# Copyright (c) 2023, asdf and Contributors
# See license.txt

import copy

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.doctype.builder_component.builder_component import (
	ComponentSyncer,
	validate_component_slots,
)
from builder.builder.doctype.builder_page.builder_page import extend_block
from builder.utils import Block


class TestBuilderComponent(FrappeTestCase):
	def test_component_slot_names_must_be_unique(self):
		block = {
			"element": "div",
			"children": [
				{"element": "div", "slotName": "content"},
				{"element": "section", "slotName": "content"},
			],
		}

		with self.assertRaises(frappe.ValidationError):
			validate_component_slots(block)

	def test_component_slots_cannot_be_nested(self):
		block = {
			"element": "div",
			"slotName": "outer",
			"children": [{"element": "div", "slotName": "inner"}],
		}

		with self.assertRaises(frappe.ValidationError):
			validate_component_slots(block)

	def test_filled_slot_replaces_fallback_when_rendering(self):
		component_slot = {
			"element": "div",
			"slotName": "content",
			"children": [{"element": "p", "innerHTML": "Fallback"}],
		}
		instance_slot = {
			"referenceBlockId": "slot",
			"slotName": "content",
			"slotFilled": True,
			"children": [{"element": "h2", "innerHTML": "Custom"}],
		}

		result = extend_block(copy.deepcopy(component_slot), instance_slot)

		self.assertEqual(result["children"], instance_slot["children"])
		self.assertNotIn("Fallback", frappe.as_json(result))

	def test_empty_filled_slot_does_not_render_fallback(self):
		component_slot = {
			"element": "div",
			"slotName": "content",
			"children": [{"element": "p", "innerHTML": "Fallback"}],
		}

		result = extend_block(
			copy.deepcopy(component_slot),
			{"slotName": "content", "slotFilled": True, "children": []},
		)

		self.assertEqual(result["children"], [])

	def test_sync_preserves_filled_slot_by_name_after_move(self):
		custom = Block(element="h2", innerHTML="Custom")
		old_slot = Block(
			blockId="instance-slot",
			referenceBlockId="old-slot",
			slotName="content",
			slotFilled=True,
			isChildOfComponent="component",
			children=[custom],
		)
		target = Block(
			extendedFromComponent="component",
			children=[Block(referenceBlockId="old-wrapper", children=[old_slot])],
		)
		new_component = Block(
			blockId="component-root",
			element="div",
			children=[
				Block(
					blockId="new-wrapper",
					element="section",
					children=[
						Block(
							blockId="new-slot",
							element="div",
							slotName="content",
							children=[Block(blockId="fallback", element="p", innerHTML="Fallback")],
						)
					],
				)
			],
		)

		ComponentSyncer(None).sync_single_block(target, "component", new_component)

		synced_slot = target.children[0].children[0]
		self.assertEqual(synced_slot.slotName, "content")
		self.assertTrue(synced_slot.slotFilled)
		self.assertEqual(synced_slot.children[0].innerHTML, "Custom")

	def test_sync_materializes_slot_defaults_as_detached_content(self):
		target = Block(
			extendedFromComponent="component",
			slotName="content",
			children=[],
		)
		component_slot = Block(
			blockId="component-slot",
			element="div",
			slotName="content",
			children=[
				Block(
					blockId="fallback",
					element="p",
					innerHTML="Fallback",
					isChildOfComponent="component",
					referenceBlockId="fallback",
				)
			],
		)

		ComponentSyncer(None).sync_single_block(target, "component", component_slot)

		self.assertTrue(target.slotFilled)
		self.assertEqual(target.children[0].innerHTML, "Fallback")
		self.assertIsNone(target.children[0].isChildOfComponent)
		self.assertIsNone(target.children[0].referenceBlockId)
