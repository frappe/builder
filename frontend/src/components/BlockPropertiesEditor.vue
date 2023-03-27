<template>
	<div :style="{
		width: `${store.builderLayout.rightPanelWidth}px`
	}">
		<PanelResizer :width="store.builderLayout.rightPanelWidth" side="left"
			@resize="width => store.builderLayout.rightPanelWidth = width" :max-width=400>
		</PanelResizer>
		<div v-if="store.builderState.selectedBlock">
			<div>
				<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Background Color</h3>
				<ul class="flex flex-wrap">
					<li v-for="color in store.pastelCssColors" :key="color" class="mr-2 mb-2 last:mr-0">
						<a @click="setBgColor(color)" class="hover:underline cursor-pointer text-base">
							<div class="w-6 h-6 rounded-md shadow-sm" :style="'background:' + color"></div>
						</a>
					</li>
				</ul>
			</div>
			<div v-if="store.builderState.selectedBlock && !store.builderState.selectedBlock.isImage()" class="mt-5">
				<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Text Color</h3>
				<ul class="flex flex-wrap">
					<li v-for="color in store.textColors" :key="color" class="mr-2 mb-2 last:mr-0">
						<a @click="setTextColor(color)" class="hover:underline cursor-pointer text-base">
							<div class="w-6 h-6 rounded-md shadow-sm" :style="'background-color:' + color"></div>
						</a>
					</li>
				</ul>
			</div>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer()"
				:value="blockStyles.display" type="select" :options="['block', 'flex', 'grid']"
				@updateValue="val => blockStyles.display = val">Layout</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer() && blockStyles.display === 'grid'"
				type="number"
				:value="blockStyles.gridTemplateRows" @updateValue="val => blockStyles.gridTemplateRows = val">Rows</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer() && blockStyles.display === 'grid'"
				type="number"
				:value="blockStyles.gridTemplateColumns" @updateValue="val => blockStyles.gridTemplateColumns = val">Columns</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer() && blockStyles.display === 'grid'"
				:value="blockStyles.gridGap" @updateValue="val => blockStyles.gridGap = val">Gap</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer() && blockStyles.display === 'grid'"
				:value="blockStyles.gridRowGap" @updateValue="val => blockStyles.gridRowGap = val">Row Gap</InlineInput>

			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer() && blockStyles.display === 'flex'"
				:value="blockStyles.flexWrap" type="select" :options="['nowrap', 'wrap', 'wrap-reverse']"
				@updateValue="val => blockStyles.flexWrap = val">Wrap</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer() && blockStyles.display === 'flex'"
				:value="blockStyles.flexDirection" type="select" :options="['row', 'row-reverse', 'column', 'column-reverse']"
				@updateValue="val => blockStyles.flexDirection = val">Direction</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer() && blockStyles.display === 'flex'"
				:value="blockStyles.justifyContent" type="select" :options="['flex-start', 'flex-end', 'center', 'space-between', 'space-around', 'space-evenly']"
				@updateValue="val => blockStyles.justifyContent = val">Justify</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer() && blockStyles.display === 'flex'"
				:value="blockStyles.alignItems" type="select" :options="['flex-start', 'flex-end', 'center', 'baseline', 'stretch']"
				@updateValue="val => blockStyles.alignItems = val">Align</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isImage()"
				:value="store.builderState.selectedBlock.attributes.src"
				@updateValue="val => store.builderState.selectedBlock.attributes.src = val">Image Source</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock.element" :value="store.builderState.selectedBlock.element"
				type="select" :options="['span', 'div', 'section', 'button', 'p', 'h1', 'h2', 'h3', 'a']"
				@updateValue="val => store.builderState.selectedBlock.element = val">Tag</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
				:value="blockStyles.fontSize" @updateValue="val => blockStyles.fontSize = val">Size</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
				:value="blockStyles.fontWeight" @updateValue="val => blockStyles.fontWeight = val">Weight</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
				:value="blockStyles.letterSpacing" @updateValue="val => blockStyles.letterSpacing = val">Spacing
			</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
				:value="blockStyles.textAlign" type="select" :options="['left', 'center', 'right', 'justify']"
				@updateValue="val => blockStyles.textAlign = val">Align</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
				:value="blockStyles.fontFamily" @updateValue="val => blockStyles.fontFamily = val">Family</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
				:value="blockStyles.lineHeight" @updateValue="val => blockStyles.lineHeight = val">Line</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer()"
				:value="blockStyles.margin" @updateValue="val => blockStyles.margin = val">Margin</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock" :value="blockStyles.height"
				@updateValue="val => blockStyles.height = val">Height</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock" :value="blockStyles.width"
				@updateValue="val => blockStyles.width = val">Width</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isLink()"
				:value="store.builderState.selectedBlock.attributes.href"
				@updateValue="val => store.builderState.selectedBlock.attributes.href = val">Link</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isButton()"
				:value="store.builderState.selectedBlock.attributes.onclick"
				@updateValue="val => store.builderState.selectedBlock.attributes.onclick = val">Action</InlineInput>
		</div>
	</div>
</template>
<script setup>
import { computed, ref } from "vue";
import PanelResizer from "./PanelResizer.vue";
import InlineInput from "./InlineInput.vue";
import useStore from "../store";
const store = useStore();

const blockStyles = computed(() => {
	let styleObj = store.builderState.selectedBlock.styles;
	if (store.builderState.activeBreakpoint === 'mobile') {
		styleObj = store.builderState.selectedBlock.mobileStyles;
	} else if (store.builderState.activeBreakpoint === 'tablet') {
		styleObj = store.builderState.selectedBlock.tabletStyles;
	}
	return styleObj;
})

const setBgColor = (color) => {
	store.builderState.selectedBlock.setStyle('background', color);
};

const setCanvasBgColor = (color) => {
	store.canvas.background = color;
};
const setTextColor = (color) => {
	store.builderState.selectedBlock.setStyle('color', color);
};

const setAlignment = (alignment) => {
	store.builderState.selectedBlock.setStyle(alignment.styleKey, alignment.styleValue);
};

const setVerticalAlignment = (alignment) => {
	store.builderState.selectedBlock.setStyle(alignment.styleKey, alignment.styleValue);
};
const setFlow = (flow) => {
	store.builderState.selectedBlock.setStyle(flow.styleKey, flow.styleValue);
};
</script>
