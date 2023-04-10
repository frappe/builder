<template>
	<div
		:style="{
			width: `${store.builderLayout.rightPanelWidth}px`,
		}">
		<PanelResizer
			:width="store.builderLayout.rightPanelWidth"
			side="left"
			@resize="(width) => (store.builderLayout.rightPanelWidth = width)"
			:max-width="400" />
		<div v-if="store.builderState.selectedBlock">
			<div>
				<h3 class="mb-1 text-xs font-bold uppercase text-gray-600">Background Color</h3>
				<ul class="flex flex-wrap">
					<li v-for="color in store.pastelCssColors" :key="color" class="mr-2 mb-2 last:mr-0">
						<a @click="setBgColor(color)" class="cursor-pointer text-base hover:underline">
							<div class="h-6 w-6 rounded-md shadow-sm" :style="'background:' + color" />
						</a>
					</li>
				</ul>
			</div>
			<div v-if="store.builderState.selectedBlock && !store.builderState.selectedBlock.isImage()" class="mt-5">
				<h3 class="mb-1 text-xs font-bold uppercase text-gray-600">Text Color</h3>
				<ul class="flex flex-wrap">
					<li v-for="color in store.textColors" :key="color" class="mr-2 mb-2 last:mr-0">
						<a @click="setTextColor(color)" class="cursor-pointer text-base hover:underline">
							<div class="h-6 w-6 rounded-md shadow-sm" :style="'background-color:' + color" />
						</a>
					</li>
				</ul>
			</div>

			<h3 v-if="store.builderState.selectedBlock" class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">
				Dimension
			</h3>
			<InlineInput
				v-if="store.builderState.selectedBlock"
				:value="blockStyles.height || 'auto'"
				@update-value="(val) => (blockStyles.height = val)">
				Height
			</InlineInput>
			<InlineInput
				v-if="store.builderState.selectedBlock"
				:value="blockStyles.width || 'auto'"
				@update-value="(val) => (blockStyles.width = val)">
				Width
			</InlineInput>
			<InlineInput
				v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer()"
				:value="blockStyles.margin"
				@update-value="(val) => (blockStyles.margin = val)">
				Margin
			</InlineInput>

			<h3
				v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer()"
				class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">
				Layout
			</h3>
			<InlineInput
				v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer()"
				:value="blockStyles.display || 'block'"
				type="select"
				:options="[
					{ label: 'Block', value: 'block' },
					{ label: 'Stack', value: 'flex' },
					{ label: 'Grid', value: 'grid' },
				]"
				@update-value="setLayout">
				Type
			</InlineInput>
			<InlineInput
				v-if="
					store.builderState.selectedBlock &&
					store.builderState.selectedBlock.isContainer() &&
					blockStyles.display === 'flex'
				"
				:value="blockStyles.flexDirection"
				type="select"
				:options="[
					{ label: 'Horizontal', value: 'row' },
					{ label: 'Vertical', value: 'column' },
				]"
				default="column"
				@update-value="(val) => (blockStyles.flexDirection = val)">
				Direction
			</InlineInput>
			<InlineInput
				v-if="
					store.builderState.selectedBlock &&
					store.builderState.selectedBlock.isContainer() &&
					blockStyles.display === 'flex'
				"
				:value="blockStyles.justifyContent"
				type="select"
				:options="[
					{
						label: blockStyles.flexDirection === 'row' ? 'Start' : 'Top',
						value: 'flex-start',
					},
					{
						label: blockStyles.flexDirection === 'row' ? 'Center' : 'Middle',
						value: 'center',
					},
					{
						label: blockStyles.flexDirection === 'row' ? 'End' : 'Bottom',
						value: 'flex-end',
					},
					{ label: 'Space Between', value: 'space-between' },
					{ label: 'Space Around', value: 'space-around' },
					{ label: 'Space Evenly', value: 'space-evenly' },
				]"
				@update-value="(val) => (blockStyles.justifyContent = val)">
				Distribute
			</InlineInput>
			<InlineInput
				v-if="
					store.builderState.selectedBlock &&
					store.builderState.selectedBlock.isContainer() &&
					blockStyles.display === 'flex'
				"
				:value="blockStyles.alignItems"
				type="select"
				:options="[
					{
						label: blockStyles.flexDirection === 'column' ? 'Start' : 'Top',
						value: 'flex-start',
					},
					{
						label: blockStyles.flexDirection === 'column' ? 'Center' : 'Middle',
						value: 'center',
					},
					{
						label: blockStyles.flexDirection === 'column' ? 'End' : 'Bottom',
						value: 'flex-end',
					},
				]"
				@update-value="(val) => (blockStyles.alignItems = val)">
				Align
			</InlineInput>
			<InlineInput
				v-if="
					store.builderState.selectedBlock &&
					store.builderState.selectedBlock.isContainer() &&
					blockStyles.display === 'flex'
				"
				:value="blockStyles.flexWrap || 'nowrap'"
				type="select"
				:options="[
					{ label: 'No Wrap', value: 'nowrap' },
					{ label: 'Wrap', value: 'wrap' },
				]"
				default="wrap"
				@update-value="(val) => (blockStyles.flexWrap = val)">
				Wrap
			</InlineInput>
			<InlineInput
				v-if="
					store.builderState.selectedBlock &&
					store.builderState.selectedBlock.isContainer() &&
					blockStyles.display === 'flex'
				"
				type="text"
				:value="blockStyles.gap"
				@update-value="(val) => (blockStyles.gap = val)">
				Gap
			</InlineInput>

			<h3 v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()" class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">
				Text
			</h3>
			<InlineInput
				v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
				:value="blockStyles.textAlign || 'left'"
				type="select"
				:options="['left', 'center', 'right', 'justify']"
				@update-value="(val) => (blockStyles.textAlign = val)">
				Align
			</InlineInput>
			<InlineInput
				v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
				:value="blockStyles.fontSize"
				@update-value="(val) => (blockStyles.fontSize = val)">
				Size
			</InlineInput>
			<InlineInput
				v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
				:value="blockStyles.fontWeight"
				@update-value="(val) => (blockStyles.fontWeight = val)">
				Weight
			</InlineInput>
			<InlineInput
				v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
				:value="blockStyles.letterSpacing"
				@update-value="(val) => (blockStyles.letterSpacing = val)">
				Spacing
			</InlineInput>
			<InlineInput
				v-if="
					store.builderState.selectedBlock &&
					(store.builderState.selectedBlock.isText() || store.builderState.selectedBlock.isRoot())
				"
				:value="blockStyles.fontFamily || 'Inter'"
				@update-value="(val) => (blockStyles.fontFamily = val)">
				Family
			</InlineInput>
			<InlineInput
				v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
				:value="blockStyles.lineHeight"
				@update-value="(val) => (blockStyles.lineHeight = val)">
				Line
			</InlineInput>
			<InlineInput
				v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isLink()"
				:value="store.builderState.selectedBlock.attributes.href"
				@update-value="(val) => (store.builderState.selectedBlock.attributes.href = val)">
				Link
			</InlineInput>
			<InlineInput
				v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isButton()"
				:value="store.builderState.selectedBlock.attributes.onclick"
				@update-value="(val) => (store.builderState.selectedBlock.attributes.onclick = val)">
				Action
			</InlineInput>
			<h3 v-if="store.builderState.selectedBlock" class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">
				Options
			</h3>
			<InlineInput
				v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isImage()"
				:value="store.builderState.selectedBlock.attributes.src"
				@update-value="(val) => (store.builderState.selectedBlock.attributes.src = val)">
				Image Source
			</InlineInput>
			<InlineInput
				v-if="store.builderState.selectedBlock.element"
				:value="store.builderState.selectedBlock.element"
				type="select"
				:options="['span', 'div', 'section', 'button', 'p', 'h1', 'h2', 'h3', 'a']"
				@update-value="(val) => (store.builderState.selectedBlock.element = val)">
				Tag
			</InlineInput>

			<InlineInput
				v-if="
					store.builderState.selectedBlock &&
					store.builderState.selectedBlock.isContainer() &&
					blockStyles.display === 'grid'
				"
				type="number"
				:value="blockStyles.gridTemplateRows"
				@update-value="(val) => (blockStyles.gridTemplateRows = val)">
				Rows
			</InlineInput>
			<InlineInput
				v-if="
					store.builderState.selectedBlock &&
					store.builderState.selectedBlock.isContainer() &&
					blockStyles.display === 'grid'
				"
				type="number"
				:value="blockStyles.gridTemplateColumns"
				@update-value="(val) => (blockStyles.gridTemplateColumns = val)">
				Columns
			</InlineInput>
			<InlineInput
				v-if="
					store.builderState.selectedBlock &&
					store.builderState.selectedBlock.isContainer() &&
					blockStyles.display === 'grid'
				"
				:value="blockStyles.gridGap"
				@update-value="(val) => (blockStyles.gridGap = val)">
				Gap
			</InlineInput>
			<InlineInput
				v-if="
					store.builderState.selectedBlock &&
					store.builderState.selectedBlock.isContainer() &&
					blockStyles.display === 'grid'
				"
				:value="blockStyles.gridRowGap"
				@update-value="(val) => (blockStyles.gridRowGap = val)">
				Row Gap
			</InlineInput>
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
	if (store.builderState.activeBreakpoint === "mobile") {
		styleObj = store.builderState.selectedBlock.mobileStyles;
	} else if (store.builderState.activeBreakpoint === "tablet") {
		styleObj = store.builderState.selectedBlock.tabletStyles;
	}
	return styleObj;
});

const setBgColor = (color) => {
	store.builderState.selectedBlock.setStyle("background", color);
};

const setLayout = (layout) => {
	let selectedBlock = store.builderState.selectedBlock;
	selectedBlock.setStyle("display", layout);
	if (layout === "flex") {
		selectedBlock.setStyle("flexDirection", selectedBlock.getStyle("flexDirection") || "row");
		selectedBlock.setStyle("flexWrap", selectedBlock.getStyle("flexWrap") || "wrap");
		selectedBlock.setStyle("justifyContent", selectedBlock.getStyle("justifyContent") || "flex-start");
		selectedBlock.setStyle("alignItems", selectedBlock.getStyle("alignItems") || "flex-start");
	} else if (layout === "grid") {
		// store.builderState.selectedBlock.setStyle("gridTemplateColumns", "repeat(3, 1fr)");
		// store.builderState.selectedBlock.setStyle("gridTemplateRows", "repeat(3, 1fr)");
		// store.builderState.selectedBlock.setStyle("gridGap", "10px");
	}
};
</script>
