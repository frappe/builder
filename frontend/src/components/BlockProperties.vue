<template>
	<div v-if="blockController.isBLockSelected()" class="flex flex-col gap-3 pb-48">
		<BLockLayoutHandler v-if="!blockController.multipleBlocksSelected()" class="mb-6"></BLockLayoutHandler>
		<div
			v-if="store.editingMode === 'component' || blockController.isRepeater()"
			class="mb-8 flex flex-col gap-3">
			<h3 class="mb-1 text-xs font-bold uppercase text-gray-600">Component Keys</h3>
			<InlineInput
				:modelValue="blockController.getDataKey('key')"
				@update:modelValue="(val) => blockController.setDataKey('key', val)">
				Key
			</InlineInput>
			<InlineInput
				:modelValue="blockController.getDataKey('type')"
				@update:modelValue="(val) => blockController.setDataKey('type', val)">
				Type
			</InlineInput>
			<InlineInput
				:modelValue="blockController.getDataKey('property')"
				@update:modelValue="(val) => blockController.setDataKey('property', val)">
				Property
			</InlineInput>
		</div>
		<h3 class="mb-1 text-xs font-bold uppercase text-gray-600">Style</h3>
		<ColorInput
			:value="blockController.getStyle('background')"
			@change="(val) => blockController.setStyle('background', val)">
			BG Color
		</ColorInput>
		<BackgroundHandler></BackgroundHandler>
		<ColorInput :value="blockController.getTextColor()" @change="(val) => blockController.setTextColor(val)">
			Text
		</ColorInput>
		<!-- border width, color -->
		<ColorInput
			:value="blockController.getStyle('borderColor')"
			@change="
				(val) => {
					blockController.setStyle('borderColor', val);
					if (val && !blockController.getStyle('borderWidth')) {
						blockController.setStyle('borderWidth', '1px');
						blockController.setStyle('borderStyle', 'solid');
					}
				}
			">
			Border Color
		</ColorInput>
		<InlineInput
			v-show="blockController.getStyle('borderColor')"
			:modelValue="blockController.getStyle('borderWidth')"
			@update:modelValue="(val) => blockController.setStyle('borderWidth', val)">
			Border Width
		</InlineInput>
		<InlineInput
			v-show="blockController.getStyle('borderColor')"
			:modelValue="blockController.getStyle('borderStyle')"
			type="select"
			:options="['solid', 'dashed', 'dotted']"
			@update:modelValue="(val) => blockController.setStyle('borderStyle', val)">
			Border Style
		</InlineInput>
		<InlineInput
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
			@update:modelValue="(val) => blockController.setStyle('boxShadow', val)">
			Shadow
		</InlineInput>

		<h3
			v-if="blockController.isText() || blockController.isContainer()"
			class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">
			Text
		</h3>
		<InlineInput
			v-if="blockController.isText()"
			:modelValue="blockController.getStyle('textAlign') || 'left'"
			type="select"
			:options="['left', 'center', 'right', 'justify']"
			@update:modelValue="(val) => blockController.setStyle('textAlign', val)">
			Align
		</InlineInput>
		<InlineInput
			v-if="blockController.isText() || blockController.isInput()"
			:modelValue="blockController.getStyle('fontSize')"
			@update:modelValue="(val) => blockController.setStyle('fontSize', val)">
			Size
		</InlineInput>
		<InlineInput
			v-if="blockController.isText()"
			:modelValue="blockController.getStyle('letterSpacing')"
			@update:modelValue="(val) => blockController.setStyle('letterSpacing', val)">
			Spacing
		</InlineInput>
		<InlineInput
			type="autocomplete"
			:options="fontListNames"
			v-if="blockController.isText() || blockController.isContainer()"
			:modelValue="blockController.getFontFamily()"
			@update:modelValue="(val) => setFont(val)">
			Family
		</InlineInput>
		<InlineInput
			v-if="blockController.isText() || blockController.isContainer()"
			:modelValue="blockController.getStyle('fontWeight')"
			type="autocomplete"
			:options="getFontWeightOptions(blockController.getStyle('fontFamily') as string || 'Inter')"
			@update:modelValue="(val) => blockController.setStyle('fontWeight', val)">
			Weight
		</InlineInput>
		<InlineInput
			v-if="blockController.isText()"
			:modelValue="blockController.getStyle('lineHeight')"
			@update:modelValue="(val) => blockController.setStyle('lineHeight', val)">
			Line
		</InlineInput>
		<div class="mt-6 flex flex-col gap-3" v-if="!blockController.isHTML() || !blockController.isRoot()">
			<h3 class="mb-1 text-xs font-bold uppercase text-gray-600">Dimension</h3>
			<DimensionInput property="width">Width</DimensionInput>
			<DimensionInput property="minWidth">Min Width</DimensionInput>
			<DimensionInput property="maxWidth">Max Width</DimensionInput>
			<hr class="dark:border-zinc-700" />
			<DimensionInput property="height">Height</DimensionInput>
			<DimensionInput property="minHeight">Min Height</DimensionInput>
			<DimensionInput property="maxHeight">Max Height</DimensionInput>
		</div>
		<BlockPositionHandler
			v-if="!blockController.multipleBlocksSelected()"
			class="mb-6"></BlockPositionHandler>

		<h3
			class="mb-1 mt-6 text-xs font-bold uppercase text-gray-600"
			v-if="!blockController.multipleBlocksSelected()">
			Spacing
		</h3>
		<InlineInput
			v-if="!blockController.multipleBlocksSelected()"
			:modelValue="blockController.getStyle('margin')"
			@update:modelValue="(val) => blockController.setStyle('margin', val)">
			Margin
		</InlineInput>
		<InlineInput
			v-if="!blockController.multipleBlocksSelected()"
			:modelValue="blockController.getStyle('padding')"
			@update:modelValue="(val) => blockController.setStyle('padding', val)">
			Padding
		</InlineInput>

		<h3 class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">Options</h3>
		<InlineInput
			v-if="blockController.isLink()"
			:modelValue="blockController.getAttribute('href')"
			@update:modelValue="(val) => blockController.setAttribute('href', val)">
			Link
		</InlineInput>
		<InlineInput
			v-if="blockController.isImage()"
			:modelValue="blockController.getAttribute('src')"
			@update:modelValue="(val) => blockController.setAttribute('src', val)">
			Image Source
		</InlineInput>
		<InlineInput
			v-if="blockController.isImage()"
			:modelValue="blockController.getStyle('objectFit')"
			type="select"
			:options="['fill', 'contain', 'cover', 'none']"
			@update:modelValue="(val) => blockController.setStyle('objectFit', val)">
			Image Fit
		</InlineInput>
		<InlineInput
			:modelValue="blockController.getKeyValue('element')"
			type="select"
			:options="['span', 'div', 'section', 'button', 'p', 'h1', 'h2', 'h3', 'a', 'input', 'hr']"
			@update:modelValue="(val) => blockController.setKeyValue('element', val)">
			Tag
		</InlineInput>
		<InlineInput
			v-if="blockController.isInput()"
			:modelValue="blockController.getAttribute('type') || 'text'"
			type="select"
			:options="['text', 'number', 'email', 'password', 'date', 'time', 'search', 'tel', 'url', 'color']"
			@update:modelValue="(val) => blockController.setAttribute('type', val)">
			Input Type
		</InlineInput>
		<!-- input placeholder -->
		<InlineInput
			v-if="blockController.isInput()"
			:modelValue="blockController.getAttribute('placeholder')"
			@update:modelValue="(val) => blockController.setAttribute('placeholder', val)">
			Placeholder
		</InlineInput>
		<InlineInput
			v-if="blockController.isText() || blockController.isButton()"
			:modelValue="blockController.getTextContent()"
			@update:modelValue="(val) => blockController.setKeyValue('innerHTML', val)">
			Content
		</InlineInput>
		<InlineInput
			v-if="blockController.isContainer() && blockController.getStyle('display') === 'grid'"
			type="number"
			:modelValue="blockController.getStyle('gridTemplateRows')"
			@update:modelValue="(val) => blockController.setStyle('gridTemplateRows', val)">
			Rows
		</InlineInput>
		<InlineInput
			v-if="blockController.isContainer() && blockController.getStyle('display') === 'grid'"
			type="number"
			:modelValue="blockController.getStyle('gridTemplateColumns')"
			@update:modelValue="(val) => blockController.setStyle('gridTemplateColumns', val)">
			Columns
		</InlineInput>
		<InlineInput
			v-if="blockController.isContainer() && blockController.getStyle('display') === 'grid'"
			:modelValue="blockController.getStyle('gridGap')"
			@update:modelValue="(val) => blockController.setStyle('gridGap', val)">
			Gap
		</InlineInput>
		<InlineInput
			v-if="blockController.isContainer() && blockController.getStyle('display') === 'grid'"
			:modelValue="blockController.getStyle('gridRowGap')"
			@update:modelValue="(val) => blockController.setStyle('gridRowGap', val)">
			Row Gap
		</InlineInput>
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
				@update:modelValue="(val) => blockController.setStyle('display', val)"></TabButtons>
		</div>
		<div class="flex items-center justify-between">
			<span class="inline-block text-[10px] font-medium uppercase text-gray-600 dark:text-zinc-400">
				Overflow
			</span>
			<TabButtons
				class="[&>div>button[aria-checked='false']]:dark:!bg-transparent [&>div>button[aria-checked='false']]:dark:!text-zinc-400 [&>div>button[aria-checked='true']]:dark:!bg-zinc-700 [&>div>button]:dark:!bg-zinc-700 [&>div>button]:dark:!text-zinc-100 [&>div]:dark:!bg-zinc-800"
				v-if="blockController.isContainer()"
				:buttons="[
					{
						label: 'Auto',
						value: 'auto',
					},
					{
						label: 'Hide',
						value: 'hidden',
					},
					{
						label: 'Scroll',
						value: 'scroll',
					},
				]"
				:modelValue="blockController.getStyle('overflow') || 'auto'"
				@update:modelValue="(val) => blockController.setStyle('overflow', val)"></TabButtons>
		</div>
		<InlineInput
			v-if="blockController.isImage()"
			:modelValue="blockController.getAttribute('alt')"
			@update:modelValue="(val) => blockController.setAttribute('alt', val)">
			Alt Text
		</InlineInput>
		<CodeEditor
			v-if="blockController.isRepeater()"
			class="mt-8"
			label="Block Data (Array)"
			:modelValue="blockController.getBlockData()"
			@update:modelValue="
				(val) => {
					blockController.setBlockData(val);
				}
			"></CodeEditor>
		<CodeEditor
			class="mt-8"
			label="RAW Styles (as JSON)"
			:modelValue="blockController.getRawStyles() || {}"
			@update:modelValue="
				(val) => {
					blockController.setRawStyles(val);
				}
			"></CodeEditor>
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
	</div>
</template>
<script setup lang="ts">
import { setFont as _setFont, fontListNames, getFontWeightOptions } from "@/utils/fontManager";
import { TabButtons } from "frappe-ui";

import BackgroundHandler from "./BackgroundHandler.vue";
import BLockLayoutHandler from "./BlockLayoutHandler.vue";
import BlockPositionHandler from "./BlockPositionHandler.vue";
import ColorInput from "./ColorInput.vue";
import InlineInput from "./InlineInput.vue";

import useStore from "@/store";
import blockController from "@/utils/blockController";
import CodeEditor from "./CodeEditor.vue";
import DimensionInput from "./DimensionInput.vue";

const store = useStore();

const setFont = (font: { value: string }) => {
	_setFont(font?.value).then(() => {
		blockController.setFontFamily(font?.value);
	});
};
</script>
