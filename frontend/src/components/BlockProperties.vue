<template>
	<div v-if="selectedBlock" class="flex flex-col gap-3">
		<BLockLayoutHandler :block="selectedBlock" v-if="selectedBlock"></BLockLayoutHandler>
		<BlockPositionHandler :block="selectedBlock" v-if="selectedBlock" class="mb-6"></BlockPositionHandler>

		<ColorInput :value="blockStyles.background" @change="(val) => selectedBlock.setStyle('background', val)">
			Background
		</ColorInput>
		<ColorInput
			:value="blockStyles.color as HashString"
			@change="(val) => selectedBlock.setStyle('color', val)">
			Text
		</ColorInput>
		<h3 v-if="selectedBlock" class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">Dimension</h3>
		<InlineInput
			v-if="selectedBlock"
			:modelValue="blockStyles.height"
			@update:modelValue="(val) => selectedBlock.setStyle('height', val)">
			Height
		</InlineInput>
		<InlineInput
			v-if="selectedBlock"
			:modelValue="blockStyles.width"
			@update:modelValue="(val) => selectedBlock.setStyle('width', val)">
			Width
		</InlineInput>
		<InlineInput
			v-if="selectedBlock"
			:modelValue="blockStyles.minWidth"
			@update:modelValue="(val) => selectedBlock.setStyle('minWidth', val)">
			Min Width
		</InlineInput>
		<InlineInput
			v-if="selectedBlock"
			:modelValue="blockStyles.maxWidth"
			@update:modelValue="(val) => selectedBlock.setStyle('maxWidth', val)">
			Max Width
		</InlineInput>
		<InlineInput
			v-if="selectedBlock"
			:modelValue="blockStyles.minHeight"
			@update:modelValue="(val) => selectedBlock.setStyle('minHeight', val)">
			Min Height
		</InlineInput>
		<InlineInput
			v-if="selectedBlock"
			:modelValue="blockStyles.maxHeight"
			@update:modelValue="(val) => selectedBlock.setStyle('maxHeight', val)">
			Max Height
		</InlineInput>
		<InlineInput
			v-if="(selectedBlock && selectedBlock.isContainer()) || selectedBlock.isButton()"
			:modelValue="blockStyles.margin"
			@update:modelValue="(val) => selectedBlock.setStyle('margin', val)">
			Margin
		</InlineInput>
		<h3
			v-if="selectedBlock && selectedBlock.isText()"
			class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">
			Text
		</h3>
		<InlineInput
			v-if="selectedBlock && selectedBlock.isText()"
			:modelValue="blockStyles.textAlign || 'left'"
			type="select"
			:options="['left', 'center', 'right', 'justify']"
			@update:modelValue="(val) => selectedBlock.setStyle('textAlign', val)">
			Align
		</InlineInput>
		<InlineInput
			v-if="selectedBlock && selectedBlock.isText()"
			:modelValue="blockStyles.fontSize"
			@update:modelValue="(val) => selectedBlock.setStyle('fontSize', val)">
			Size
		</InlineInput>
		<InlineInput
			v-if="selectedBlock && selectedBlock.isText()"
			:modelValue="blockStyles.letterSpacing"
			@update:modelValue="(val) => selectedBlock.setStyle('letterSpacing', val)">
			Spacing
		</InlineInput>
		<InlineInput
			type="autocomplete"
			:options="fontListNames"
			v-if="selectedBlock && (selectedBlock.isText() || selectedBlock.isContainer())"
			:modelValue="blockStyles.fontFamily || 'Inter'"
			@update:modelValue="(val) => setFont(val)">
			Family
		</InlineInput>
		<InlineInput
			v-if="selectedBlock && (selectedBlock.isText() || selectedBlock.isContainer())"
			:modelValue="blockStyles.fontWeight"
			type="select"
			:options="getFontWeightOptions(blockStyles.fontFamily as string || 'Inter')"
			@update:modelValue="(val) => selectedBlock.setStyle('fontWeight', val)">
			Weight
		</InlineInput>
		<InlineInput
			v-if="selectedBlock && selectedBlock.isText()"
			:modelValue="blockStyles.lineHeight"
			@update:modelValue="(val) => selectedBlock.setStyle('lineHeight', val)">
			Line
		</InlineInput>
		<InlineInput
			v-if="selectedBlock && selectedBlock.isLink()"
			:modelValue="selectedBlock.attributes.href"
			@update:modelValue="(val) => (selectedBlock.attributes.href = val)">
			Link
		</InlineInput>
		<h3 v-if="selectedBlock" class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">Options</h3>
		<InlineInput
			v-if="selectedBlock && selectedBlock.isImage()"
			:modelValue="selectedBlock.attributes.src"
			@update:modelValue="(val) => (selectedBlock.attributes.src = val)">
			Image Source
		</InlineInput>
		<InlineInput
			v-if="selectedBlock && selectedBlock.isButton()"
			:modelValue="selectedBlock.attributes.onclick"
			@update:modelValue="(val) => (selectedBlock.attributes.onclick = val)">
			Action
		</InlineInput>
		<InlineInput
			v-if="selectedBlock.element"
			:modelValue="selectedBlock.element"
			type="select"
			:options="['span', 'div', 'section', 'button', 'p', 'h1', 'h2', 'h3', 'a']"
			@update:modelValue="(val) => (selectedBlock.element = val)">
			Tag
		</InlineInput>

		<InlineInput
			v-if="selectedBlock && selectedBlock.isContainer() && blockStyles.display === 'grid'"
			type="number"
			:modelValue="blockStyles.gridTemplateRows"
			@update:modelValue="(val) => selectedBlock.setStyle('gridTemplateRows', val)">
			Rows
		</InlineInput>
		<InlineInput
			v-if="selectedBlock && selectedBlock.isContainer() && blockStyles.display === 'grid'"
			type="number"
			:modelValue="blockStyles.gridTemplateColumns"
			@update:modelValue="(val) => selectedBlock.setStyle('gridTemplateColumns', val)">
			Columns
		</InlineInput>
		<InlineInput
			v-if="selectedBlock && selectedBlock.isContainer() && blockStyles.display === 'grid'"
			:modelValue="blockStyles.gridGap"
			@update:modelValue="(val) => selectedBlock.setStyle('gridGap', val)">
			Gap
		</InlineInput>
		<InlineInput
			v-if="selectedBlock && selectedBlock.isContainer() && blockStyles.display === 'grid'"
			:modelValue="blockStyles.gridRowGap"
			@update:modelValue="(val) => selectedBlock.setStyle('gridRowGap', val)">
			Row Gap
		</InlineInput>
		<!-- overflow -->
		<InlineInput
			v-if="selectedBlock && selectedBlock.isContainer()"
			type="select"
			:options="['visible', 'hidden', 'scroll']"
			:modelValue="blockStyles.overflow"
			@update:modelValue="(val) => selectedBlock.setStyle('overflow', val)">
			Overflow
		</InlineInput>
		<!-- shadow -->
		<InlineInput
			v-if="selectedBlock && selectedBlock.isContainer()"
			type="select"
			:options="[
				{
					value: 'none',
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
			:modelValue="blockStyles.boxShadow"
			@update:modelValue="(val) => selectedBlock.setStyle('boxShadow', val)">
			Shadow
		</InlineInput>

		<h3 v-if="selectedBlock" class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">RAW Styles</h3>
		<div id="editor" class="border border-gray-200 dark:border-zinc-800" />
	</div>
</template>
<script setup lang="ts">
import useStore from "@/store";
import Block from "@/utils/block";
import { setFont as _setFont, fontListNames, getFontWeightOptions } from "@/utils/fontManager";
import { useDark } from "@vueuse/core";
import { PropType, computed, onMounted, watch, watchEffect } from "vue";
import BLockLayoutHandler from "./BlockLayoutHandler.vue";
import BlockPositionHandler from "./BlockPositionHandler.vue";
import ColorInput from "./ColorInput.vue";
import InlineInput from "./InlineInput.vue";

const isDark = useDark();

import ace from "ace-builds";
import "ace-builds/src-noconflict/mode-json";
import "ace-builds/src-noconflict/theme-chrome";
import "ace-builds/src-noconflict/theme-monokai";

const store = useStore();

const props = defineProps({
	selectedBlock: {
		type: Object as PropType<Block>,
		required: true,
	},
});

const blockStyles = computed(() => {
	let styleObj = props.selectedBlock.baseStyles;
	if (store.builderState.activeBreakpoint === "mobile") {
		styleObj = { ...styleObj, ...props.selectedBlock.mobileStyles };
	} else if (store.builderState.activeBreakpoint === "tablet") {
		styleObj = { ...styleObj, ...props.selectedBlock.tabletStyles };
	}
	return styleObj;
});

const setBgColor = (color: HashString) => {
	props.selectedBlock.setStyle("background", color);
};

const setFont = (font: { value: string }) => {
	_setFont(font.value).then(() => {
		props.selectedBlock.setStyle("fontFamily", font.value);
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
	editor.setValue(JSON.stringify(props.selectedBlock.rawStyles, null, 2));
	editor.on("blur", () => {
		const value = editor.getValue();
		try {
			const parsed = JSON.parse(value);
			props.selectedBlock.rawStyles = parsed;
		} catch (e) {
			// console.error(e);
		}
	});

	watch(props, () => {
		editor.setValue(JSON.stringify(props.selectedBlock.rawStyles, null, 2));
	});

	watchEffect(() => {
		if (isDark.value) {
			editor.setTheme("ace/theme/monokai");
		} else {
			editor.setTheme("ace/theme/chrome");
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
