<template>
	<div v-if="selectedBlock" class="flex flex-col">
		<BLockLayoutHandler :block="selectedBlock" v-if="selectedBlock"></BLockLayoutHandler>
		<BlockPositionHandler :block="selectedBlock" v-if="selectedBlock"></BlockPositionHandler>

		<InlineInput :modelValue="blockStyles.background" @update:modelValue="setBgColor" class="mt-10">
			Background
		</InlineInput>
		<div class="mt-3">
			<ul class="flex flex-wrap gap-2">
				<li v-for="color in store.pastelCssColors" :key="color">
					<a @click="setBgColor(color as HashString)" class="cursor-pointer text-base hover:underline">
						<div class="h-4 w-4 rounded-md shadow-sm" :style="'background:' + color" />
					</a>
				</li>
			</ul>
		</div>
		<ColorInput :value="blockStyles.color" @change="(val) => (blockStyles.color = val)"></ColorInput>
		<h3 v-if="selectedBlock" class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">Dimension</h3>
		<InlineInput
			v-if="selectedBlock"
			:modelValue="blockStyles.height || 'unset'"
			@update:modelValue="(val) => (blockStylesObj.height = val)">
			Height
		</InlineInput>
		<InlineInput
			v-if="selectedBlock"
			:modelValue="blockStyles.width || 'unset'"
			@update:modelValue="(val) => (blockStylesObj.width = val)">
			Width
		</InlineInput>
		<InlineInput
			v-if="selectedBlock"
			:modelValue="blockStyles.minWidth || 'unset'"
			@update:modelValue="(val) => (blockStylesObj.minWidth = val)">
			Min Width
		</InlineInput>
		<InlineInput
			v-if="selectedBlock"
			:modelValue="blockStyles.maxWidth || 'unset'"
			@update:modelValue="(val) => (blockStylesObj.maxWidth = val)">
			Max Width
		</InlineInput>
		<InlineInput
			v-if="selectedBlock"
			:modelValue="blockStyles.minHeight || 'unset'"
			@update:modelValue="(val) => (blockStylesObj.minHeight = val)">
			Min Height
		</InlineInput>
		<InlineInput
			v-if="selectedBlock"
			:modelValue="blockStyles.maxHeight || 'unset'"
			@update:modelValue="(val) => (blockStylesObj.maxHeight = val)">
			Max Height
		</InlineInput>
		<InlineInput
			v-if="(selectedBlock && selectedBlock.isContainer()) || selectedBlock.isButton()"
			:modelValue="blockStyles.margin"
			@update:modelValue="(val) => (blockStylesObj.margin = val)">
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
			@update:modelValue="(val) => (blockStylesObj.textAlign = val)">
			Align
		</InlineInput>
		<InlineInput
			v-if="selectedBlock && selectedBlock.isText()"
			:modelValue="blockStyles.fontSize"
			@update:modelValue="(val) => (blockStylesObj.fontSize = val)">
			Size
		</InlineInput>
		<InlineInput
			v-if="selectedBlock && selectedBlock.isText()"
			:modelValue="blockStyles.letterSpacing"
			@update:modelValue="(val) => (blockStylesObj.letterSpacing = val)">
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
			@update:modelValue="(val) => (blockStylesObj.fontWeight = val)">
			Weight
		</InlineInput>
		<InlineInput
			v-if="selectedBlock && selectedBlock.isText()"
			:modelValue="blockStyles.lineHeight"
			@update:modelValue="(val) => (blockStylesObj.lineHeight = val)">
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
			@update:modelValue="(val) => (blockStylesObj.gridTemplateRows = val)">
			Rows
		</InlineInput>
		<InlineInput
			v-if="selectedBlock && selectedBlock.isContainer() && blockStyles.display === 'grid'"
			type="number"
			:modelValue="blockStyles.gridTemplateColumns"
			@update:modelValue="(val) => (blockStylesObj.gridTemplateColumns = val)">
			Columns
		</InlineInput>
		<InlineInput
			v-if="selectedBlock && selectedBlock.isContainer() && blockStyles.display === 'grid'"
			:modelValue="blockStyles.gridGap"
			@update:modelValue="(val) => (blockStylesObj.gridGap = val)">
			Gap
		</InlineInput>
		<InlineInput
			v-if="selectedBlock && selectedBlock.isContainer() && blockStyles.display === 'grid'"
			:modelValue="blockStyles.gridRowGap"
			@update:modelValue="(val) => (blockStylesObj.gridRowGap = val)">
			Row Gap
		</InlineInput>
		<!-- overflow -->
		<InlineInput
			v-if="selectedBlock && selectedBlock.isContainer()"
			type="select"
			:options="['visible', 'hidden', 'scroll']"
			:modelValue="blockStyles.overflow"
			@update:modelValue="(val) => (blockStyles.overflow = val)">
			Overflow
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

// TODO: Temporary for correctness, remove when we have a better way to handle this
const blockStylesObj = computed(() => {
	let styleObj = props.selectedBlock.baseStyles;
	if (store.builderState.activeBreakpoint === "mobile") {
		styleObj = props.selectedBlock.mobileStyles;
	} else if (store.builderState.activeBreakpoint === "tablet") {
		styleObj = props.selectedBlock.tabletStyles;
	}
	return styleObj;
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
