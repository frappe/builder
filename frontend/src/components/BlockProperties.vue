<!-- TODO: Refactor -->
<template>
	<div v-if="blockController.isBLockSelected()" class="mt-[-10px] flex select-none flex-col gap-3 pb-16">
		<CollapsibleSection sectionName="Layout" v-if="!blockController.multipleBlocksSelected()">
			<BLockLayoutHandler></BLockLayoutHandler>
		</CollapsibleSection>
		<CollapsibleSection sectionName="Style">
			<ColorInput
				label="BG Color"
				:value="blockController.getStyle('background')"
				@change="(val) => blockController.setStyle('background', val)" />
			<ColorInput
				label="Text Color"
				:value="blockController.getTextColor()"
				@change="(val) => blockController.setTextColor(val)" />
			<ColorInput
				label="Border Color"
				:value="blockController.getStyle('borderColor')"
				@change="
					(val) => {
						blockController.setStyle('borderColor', val);
						if (val && !blockController.getStyle('borderWidth')) {
							blockController.setStyle('borderWidth', '1px');
							blockController.setStyle('borderStyle', 'solid');
						}
					}
				"></ColorInput>
			<BackgroundHandler></BackgroundHandler>
			<InlineInput
				label="Border Width"
				v-show="blockController.getStyle('borderColor')"
				:modelValue="blockController.getStyle('borderWidth')"
				@update:modelValue="(val) => blockController.setStyle('borderWidth', val)" />

			<InlineInput
				label="Border Style"
				v-show="blockController.getStyle('borderColor')"
				:modelValue="blockController.getStyle('borderStyle')"
				type="select"
				:options="['solid', 'dashed', 'dotted']"
				@update:modelValue="(val) => blockController.setStyle('borderStyle', val)" />
			<InlineInput
				label="Shadow"
				type="select"
				:options="[
					{
						value: null,
						label: 'None',
					},
					{
						label: 'Small',
						value:
							'rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.05) 0px 1px 2px 0px, rgba(0, 0, 0, 0.05) 0px 1px 3px 0px',
					},
					{
						label: 'Medium',
						value:
							'rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.1) 0px 10px 15px -3px, rgba(0, 0, 0, 0.1) 0px 4px 6px -4px',
					},
					{
						label: 'Large',
						value:
							'rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.1) 0px 20px 25px -5px, rgba(0, 0, 0, 0.1) 0px 10px 10px -5px',
					},
				]"
				:modelValue="blockController.getStyle('boxShadow')"
				@update:modelValue="(val) => blockController.setStyle('boxShadow', val)"></InlineInput>
			<InlineInput
				label="Border Radius"
				:modelValue="blockController.getStyle('borderRadius')"
				:enableSlider="true"
				:unitOptions="['px', '%']"
				:minValue="0"
				@update:modelValue="(val) => blockController.setStyle('borderRadius', val)" />
			<InlineInput
				v-if="
					!blockController.multipleBlocksSelected() &&
					!blockController.isRoot() &&
					blockController.getStyle('position') !== 'static'
				"
				label="Z-Index"
				:modelValue="blockController.getStyle('zIndex')"
				@update:modelValue="(val) => blockController.setStyle('zIndex', val)" />
		</CollapsibleSection>
		<CollapsibleSection
			sectionName="Typography"
			v-if="blockController.isText() || blockController.isContainer()">
			<InlineInput
				label="Family"
				type="autocomplete"
				:options="fontListNames"
				v-if="blockController.isText() || blockController.isContainer()"
				:modelValue="blockController.getFontFamily()"
				@update:modelValue="(val) => setFont(val)" />
			<InlineInput
				label="Weight"
				v-if="blockController.isText() || blockController.isContainer()"
				:modelValue="blockController.getStyle('fontWeight')"
				type="autocomplete"
				:options="getFontWeightOptions(blockController.getStyle('fontFamily') as string || 'Inter')"
				@update:modelValue="(val) => blockController.setStyle('fontWeight', val)" />
			<InlineInput
				label="Size"
				v-if="blockController.isText() || blockController.isInput()"
				:modelValue="blockController.getStyle('fontSize')"
				:enableSlider="true"
				@update:modelValue="(val) => blockController.setStyle('fontSize', val)" />
			<InlineInput
				label="Height"
				v-if="blockController.isText()"
				:modelValue="blockController.getStyle('lineHeight')"
				@update:modelValue="(val) => blockController.setStyle('lineHeight', val)" />
			<InlineInput
				label="Letter"
				v-if="blockController.isText()"
				:modelValue="blockController.getStyle('letterSpacing')"
				@update:modelValue="(val) => blockController.setStyle('letterSpacing', val)" />
			<InlineInput
				label="Transform"
				v-if="blockController.isText()"
				:modelValue="blockController.getStyle('textTransform')"
				type="select"
				:options="[
					{
						value: null,
						label: 'None',
					},
					{
						value: 'uppercase',
						label: 'Uppercase',
					},
					{
						value: 'lowercase',
						label: 'Lowercase',
					},
					{
						value: 'capitalize',
						label: 'Capitalize',
					},
				]"
				@update:modelValue="(val) => blockController.setStyle('textTransform', val)" />
			<InlineInput
				label="Align"
				v-if="blockController.isText()"
				:modelValue="blockController.getStyle('textAlign') || 'left'"
				type="select"
				:options="['left', 'center', 'right', 'justify']"
				@update:modelValue="(val) => blockController.setStyle('textAlign', val)"></InlineInput>
		</CollapsibleSection>
		<CollapsibleSection sectionName="Dimension">
			<DimensionInput label="Width" property="width" />
			<DimensionInput label="Min Width" property="minWidth" />
			<DimensionInput label="Max Width" property="maxWidth" />
			<hr class="dark:border-zinc-700" />
			<DimensionInput label="Height" property="height" />
			<DimensionInput label="Min Height" property="minHeight" />
			<DimensionInput label="Max Height" property="maxHeight" />
		</CollapsibleSection>
		<CollapsibleSection sectionName="Position" v-if="!blockController.multipleBlocksSelected()">
			<BlockPositionHandler></BlockPositionHandler>
		</CollapsibleSection>
		<CollapsibleSection sectionName="Spacing" v-if="!blockController.multipleBlocksSelected()">
			<InlineInput
				label="Margin"
				v-if="!blockController.multipleBlocksSelected() && !blockController.isRoot()"
				:modelValue="blockController.getStyle('margin')"
				@update:modelValue="(val) => blockController.setStyle('margin', val)" />
			<InlineInput
				label="Padding"
				v-if="!blockController.multipleBlocksSelected()"
				:modelValue="blockController.getPadding()"
				@update:modelValue="(val) => blockController.setPadding(val)" />
		</CollapsibleSection>
		<CollapsibleSection sectionName="Options">
			<InlineInput
				label="Link"
				v-if="blockController.isLink()"
				:modelValue="blockController.getAttribute('href')"
				@update:modelValue="(val) => blockController.setAttribute('href', val)" />
			<InlineInput
				label="Image URL"
				v-if="blockController.isImage()"
				:modelValue="blockController.getAttribute('src')"
				@update:modelValue="(val) => blockController.setAttribute('src', val)" />
			<InlineInput
				label="Image Fit"
				v-if="blockController.isImage()"
				:modelValue="blockController.getStyle('objectFit')"
				type="select"
				:options="['fill', 'contain', 'cover', 'none']"
				@update:modelValue="(val) => blockController.setStyle('objectFit', val)" />
			<InlineInput
				label="Tag"
				:modelValue="blockController.getKeyValue('element')"
				type="select"
				:options="['span', 'div', 'section', 'button', 'p', 'h1', 'h2', 'h3', 'a', 'input', 'hr']"
				@update:modelValue="(val) => blockController.setKeyValue('element', val)" />
			<InlineInput
				label="Input Type"
				v-if="blockController.isInput()"
				:modelValue="blockController.getAttribute('type') || 'text'"
				type="select"
				:options="['text', 'number', 'email', 'password', 'date', 'time', 'search', 'tel', 'url', 'color']"
				@update:modelValue="(val) => blockController.setAttribute('type', val)" />
			<!-- input placeholder -->
			<InlineInput
				label="Placeholder"
				v-if="blockController.isInput()"
				:modelValue="blockController.getAttribute('placeholder')"
				@update:modelValue="(val) => blockController.setAttribute('placeholder', val)" />
			<InlineInput
				label="Content"
				v-if="blockController.isText() || blockController.isButton()"
				:modelValue="blockController.getTextContent()"
				@update:modelValue="(val) => blockController.setKeyValue('innerHTML', val)" />
			<div class="flex items-center justify-between">
				<span class="inline-block text-[10px] font-medium uppercase text-gray-600 dark:text-zinc-400">
					Visibility
				</span>
				<TabButtons
					class="[&>div>button[aria-checked='false']]:dark:!bg-transparent [&>div>button[aria-checked='false']]:dark:!text-zinc-400 [&>div>button[aria-checked='true']]:dark:!bg-zinc-700 [&>div>button]:dark:!bg-zinc-700 [&>div>button]:dark:!text-zinc-100 [&>div]:dark:!bg-zinc-800"
					:buttons="[
						{
							label: 'Visible',
							value: 'flex',
						},
						{
							label: 'Hidden',
							value: 'none',
						},
					]"
					:modelValue="blockController.getStyle('display') || 'flex'"
					@update:modelValue="(val: string) => blockController.setStyle('display', val)"></TabButtons>
			</div>
			<div class="flex items-center justify-between">
				<span class="inline-block text-[10px] font-medium uppercase text-gray-600 dark:text-zinc-400">
					Overflow
				</span>
				<div class="flex w-[150px] gap-2">
					<Input
						type="select"
						:modelValue="blockController.getStyle('overflowX') || 'auto'"
						:options="['auto', 'hidden', 'scroll']"
						@change="(val: string) => blockController.setStyle('overflowX', val)"
						class="flex-1 rounded-md text-sm text-gray-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:focus:bg-zinc-700" />
					<Input
						type="select"
						:modelValue="blockController.getStyle('overflowY') || 'auto'"
						:options="['auto', 'hidden', 'scroll']"
						@change="(val: string) => blockController.setStyle('overflowY', val)"
						class="flex-1 rounded-md text-sm text-gray-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:focus:bg-zinc-700" />
				</div>
			</div>
			<InlineInput
				label="Alt Text"
				v-if="blockController.isImage()"
				:modelValue="blockController.getAttribute('alt')"
				@update:modelValue="(val) => blockController.setAttribute('alt', val)" />

			<InlineInput
				label="Class"
				v-if="!blockController.multipleBlocksSelected()"
				:modelValue="getClasses()"
				@update:modelValue="(val) => setClasses(val)" />
			<CodeEditor
				v-if="blockController.isHTML()"
				class="mt-8"
				label="HTML"
				type="HTML"
				:modelValue="blockController.getInnerHTML() || ''"
				@update:modelValue="
					(val) => {
						blockController.setInnerHTML(val);
					}
				"></CodeEditor>
		</CollapsibleSection>
		<CollapsibleSection sectionName="Data Key">
			<InlineInput
				label="Key"
				:modelValue="blockController.getDataKey('key')"
				@update:modelValue="(val) => blockController.setDataKey('key', val)" />
			<InlineInput
				label="Type"
				:modelValue="blockController.getDataKey('type')"
				@update:modelValue="(val) => blockController.setDataKey('type', val)" />
			<InlineInput
				label="Property"
				:modelValue="blockController.getDataKey('property')"
				@update:modelValue="(val) => blockController.setDataKey('property', val)" />
		</CollapsibleSection>
	</div>
	<div v-else>
		<p class="text-center text-sm text-gray-600 dark:text-zinc-500">Select a block to edit properties.</p>
	</div>
</template>
<script setup lang="ts">
import { setFont as _setFont, fontListNames, getFontWeightOptions } from "@/utils/fontManager";
import { TabButtons } from "frappe-ui";

import BackgroundHandler from "./BackgroundHandler.vue";
import BLockLayoutHandler from "./BlockLayoutHandler.vue";
import BlockPositionHandler from "./BlockPositionHandler.vue";
import CollapsibleSection from "./CollapsibleSection.vue";
import ColorInput from "./ColorInput.vue";
import InlineInput from "./InlineInput.vue";

import blockController from "@/utils/blockController";
import CodeEditor from "./CodeEditor.vue";
import DimensionInput from "./DimensionInput.vue";

const setFont = (font: string) => {
	_setFont(font).then(() => {
		blockController.setFontFamily(font);
	});
};

const getClasses = () => {
	return blockController.getClasses().join(", ");
};

const setClasses = (val: string) => {
	const classes = val.split(",").map((c) => c.trim());
	blockController.setClasses(classes);
};
</script>
