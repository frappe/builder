<template>
	<div v-if="blockController.isBLockSelected()" class="flex flex-col gap-3">
		<BLockLayoutHandler v-if="!blockController.multipleBlocksSelected()" class="mb-6"></BLockLayoutHandler>
		<BlockPositionHandler
			v-if="!blockController.multipleBlocksSelected()"
			class="mb-6"></BlockPositionHandler>
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
		<div class="flex flex-col gap-3" v-if="!blockController.isHTML() || !blockController.isRoot()">
			<h3 class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">Dimension</h3>
			<InlineInput
				:modelValue="blockController.getStyle('height')"
				@update:modelValue="(val) => blockController.setStyle('height', val)">
				Height
			</InlineInput>
			<InlineInput
				:modelValue="blockController.getStyle('width')"
				@update:modelValue="(val) => blockController.setStyle('width', val)">
				Width
			</InlineInput>
			<InlineInput
				:modelValue="blockController.getStyle('minWidth')"
				@update:modelValue="(val) => blockController.setStyle('minWidth', val)">
				Min Width
			</InlineInput>
			<InlineInput
				:modelValue="blockController.getStyle('maxWidth')"
				@update:modelValue="(val) => blockController.setStyle('maxWidth', val)">
				Max Width
			</InlineInput>
			<InlineInput
				:modelValue="blockController.getStyle('minHeight')"
				@update:modelValue="(val) => blockController.setStyle('minHeight', val)">
				Min Height
			</InlineInput>
			<InlineInput
				:modelValue="blockController.getStyle('maxHeight')"
				@update:modelValue="(val) => blockController.setStyle('maxHeight', val)">
				Max Height
			</InlineInput>
		</div>

		<h3
			class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600"
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
			v-if="blockController.isText()"
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
			type="select"
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
			@update:modelValue="(val) => blockController.setAttribute('href', val)">
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
			:modelValue="blockController.getKeyValue('innerText')"
			@update:modelValue="(val) => blockController.setKeyValue('innerText', val)">
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
		<!-- overflow -->
		<InlineInput
			v-if="blockController.isContainer()"
			type="select"
			:options="[
				{
					label: 'Visible',
					value: '',
				},
				{
					label: 'Hidden',
					value: 'hidden',
				},
				{
					label: 'Scroll',
					value: 'scroll',
				},
				{
					label: 'Auto',
					value: 'auto',
				},
			]"
			:modelValue="blockController.getStyle('overflow')"
			@update:modelValue="(val) => blockController.setStyle('overflow', val)">
			Overflow
		</InlineInput>

		<h3 class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">RAW Styles</h3>
		<div id="editor" class="border border-gray-200 dark:border-zinc-800" />
		<Input
			v-show="blockController.isHTML()"
			type="textarea"
			label="HTML"
			class="mb-8 h-36"
			id="html"
			@change="(val) => blockController.setInnerHTML(val)"
			:value="blockController.getInnerHTML()" />
	</div>
</template>
<script setup lang="ts">
import { setFont as _setFont, fontListNames, getFontWeightOptions } from "@/utils/fontManager";
import { useDark } from "@vueuse/core";
import { onMounted, watchEffect } from "vue";
import BackgroundHandler from "./BackgroundHandler.vue";
import BLockLayoutHandler from "./BlockLayoutHandler.vue";
import BlockPositionHandler from "./BlockPositionHandler.vue";
import ColorInput from "./ColorInput.vue";
import InlineInput from "./InlineInput.vue";

import blockController from "@/utils/blockController";
import ace from "ace-builds";
import "ace-builds/src-noconflict/mode-html";
import "ace-builds/src-noconflict/mode-json";
import "ace-builds/src-noconflict/theme-chrome";
import "ace-builds/src-noconflict/theme-monokai";

const isDark = useDark();

const setFont = (font: { value: string }) => {
	_setFont(font.value).then(() => {
		blockController.setFontFamily(font.value);
	});
};

onMounted(() => {
	const editor = ace.edit("editor");
	editor.setOptions({
		fontSize: "12px",
		useWorker: false,
		showGutter: false,
	});
	editor.setTheme("ace/theme/chrome");
	editor.session.setMode("ace/mode/json");
	editor.setValue(JSON.stringify(blockController.getRawStyles(), null, 2));
	editor.on("blur", () => {
		const value = editor.getValue();
		try {
			const parsed = JSON.parse(value) as BlockStyleMap;
			blockController.setRawStyles(parsed);
		} catch (e) {
			// console.error(e);
		}
	});

	const htmlEditor = ace.edit("html");
	htmlEditor.setOptions({
		fontSize: "12px",
		useWorker: false,
		showGutter: false,
	});
	htmlEditor.setTheme("ace/theme/chrome");
	htmlEditor.session.setMode("ace/mode/html");
	htmlEditor.on("blur", () => {
		const value = htmlEditor.getValue();
		blockController.setInnerHTML(value);
	});

	watchEffect(() => {
		editor.setValue(JSON.stringify(blockController.getRawStyles(), null, 2));
	});

	watchEffect(() => {
		htmlEditor.setValue(blockController.getInnerHTML() as string);
	});

	watchEffect(() => {
		if (isDark.value) {
			editor.setTheme("ace/theme/monokai");
			htmlEditor.setTheme("ace/theme/monokai");
		} else {
			editor.setTheme("ace/theme/chrome");
			htmlEditor.setTheme("ace/theme/chrome");
		}
	});
});
</script>
<style scoped>
:deep(.ace_editor) {
	height: 200px;
	width: 100%;
	border-radius: 5px;
}
</style>
