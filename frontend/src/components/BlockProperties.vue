<template>
	<div v-if="store.builderState.selectedBlock">
		<div>
			<h3 class="mb-1 text-xs font-bold uppercase text-gray-600">Background Color</h3>
			<ul class="flex flex-wrap">
				<li v-for="color in store.pastelCssColors" :key="color" class="mb-2 mr-2 last:mr-0">
					<a @click="setBgColor(color)" class="cursor-pointer text-base hover:underline">
						<div class="h-4 w-4 rounded-md shadow-sm" :style="'background:' + color" />
					</a>
				</li>
			</ul>
		</div>
		<InlineInput :value="blockStyles.background" @update-value="setBgColor">Background</InlineInput>
		<div v-if="store.builderState.selectedBlock && !store.builderState.selectedBlock.isImage()" class="mt-5">
			<h3 class="mb-1 text-xs font-bold uppercase text-gray-600">Text Color</h3>
			<ul class="flex flex-wrap">
				<li v-for="color in store.textColors" :key="color" class="mb-2 mr-2 last:mr-0">
					<a @click="blockStyles.color = color" class="cursor-pointer text-base hover:underline">
						<div class="h-4 w-4 rounded-md shadow-sm" :style="'background-color:' + color" />
					</a>
				</li>
			</ul>
		</div>
		<InlineInput :value="blockStyles.color" @update-value="(color) => (blockStyles.color = color)">
			Text Color
		</InlineInput>

		<h3 v-if="store.builderState.selectedBlock" class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">
			Position
		</h3>
		<!-- position with options [absolute, relative, static]-->
		<InlineInput
			v-if="store.builderState.selectedBlock"
			:value="blockStyles.position || 'static'"
			type="select"
			:options="['static', 'relative', 'absolute', 'fixed', 'sticky']"
			@update-value="(val) => (blockStylesObj.position = val)">
			Position
		</InlineInput>
		<InlineInput
			v-if="store.builderState.selectedBlock"
			:value="blockStyles.top || 'unset'"
			@update-value="(val) => (blockStylesObj.top = val)">
			Top
		</InlineInput>
		<InlineInput
			v-if="store.builderState.selectedBlock"
			:value="blockStyles.right || 'unset'"
			@update-value="(val) => (blockStylesObj.right = val)">
			Right
		</InlineInput>
		<InlineInput
			v-if="store.builderState.selectedBlock"
			:value="blockStyles.bottom || 'unset'"
			@update-value="(val) => (blockStylesObj.bottom = val)">
			Bottom
		</InlineInput>
		<InlineInput
			v-if="store.builderState.selectedBlock"
			:value="blockStyles.left || 'unset'"
			@update-value="(val) => (blockStylesObj.left = val)">
			Left
		</InlineInput>

		<h3 v-if="store.builderState.selectedBlock" class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">
			Dimension
		</h3>
		<InlineInput
			v-if="store.builderState.selectedBlock"
			:value="blockStyles.height || 'unset'"
			@update-value="(val) => (blockStylesObj.height = val)">
			Height
		</InlineInput>
		<InlineInput
			v-if="store.builderState.selectedBlock"
			:value="blockStyles.width || 'unset'"
			@update-value="(val) => (blockStylesObj.width = val)">
			Width
		</InlineInput>
		<InlineInput
			v-if="store.builderState.selectedBlock"
			:value="blockStyles.minWidth || 'unset'"
			@update-value="(val) => (blockStylesObj.minWidth = val)">
			Min Width
		</InlineInput>
		<InlineInput
			v-if="store.builderState.selectedBlock"
			:value="blockStyles.maxWidth || 'unset'"
			@update-value="(val) => (blockStylesObj.maxWidth = val)">
			Max Width
		</InlineInput>
		<InlineInput
			v-if="store.builderState.selectedBlock"
			:value="blockStyles.minHeight || 'unset'"
			@update-value="(val) => (blockStylesObj.minHeight = val)">
			Min Height
		</InlineInput>
		<InlineInput
			v-if="store.builderState.selectedBlock"
			:value="blockStyles.maxHeight || 'unset'"
			@update-value="(val) => (blockStylesObj.maxHeight = val)">
			Max Height
		</InlineInput>
		<InlineInput
			v-if="
				(store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer()) ||
				store.builderState.selectedBlock.isButton()
			"
			:value="blockStyles.margin"
			@update-value="(val) => (blockStylesObj.margin = val)">
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
			@update-value="(val) => (blockStylesObj.flexDirection = val)">
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
			@update-value="(val) => (blockStylesObj.justifyContent = val)">
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
			@update-value="(val) => (blockStylesObj.alignItems = val)">
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
			@update-value="(val) => (blockStylesObj.flexWrap = val)">
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
			@update-value="(val) => (blockStylesObj.gap = val)">
			Gap
		</InlineInput>
		<!-- flex basis -->
		<InlineInput
			v-if="
				store.builderState.selectedBlock &&
				store.builderState.selectedBlock.isContainer() &&
				blockStyles.display === 'flex'
			"
			type="text"
			:value="blockStyles.flexBasis"
			@update-value="(val) => (blockStylesObj.flexBasis = val)">
			Basis
		</InlineInput>
		<h3
			v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
			class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">
			Text
		</h3>
		<InlineInput
			v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
			:value="blockStyles.textAlign || 'left'"
			type="select"
			:options="['left', 'center', 'right', 'justify']"
			@update-value="(val) => (blockStylesObj.textAlign = val)">
			Align
		</InlineInput>
		<InlineInput
			v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
			:value="blockStyles.fontSize"
			@update-value="(val) => (blockStylesObj.fontSize = val)">
			Size
		</InlineInput>
		<InlineInput
			v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
			:value="blockStyles.letterSpacing"
			@update-value="(val) => (blockStylesObj.letterSpacing = val)">
			Spacing
		</InlineInput>
		<InlineInput
			type="autocomplete"
			:options="fontListNames"
			v-if="
				store.builderState.selectedBlock &&
				(store.builderState.selectedBlock.isText() || store.builderState.selectedBlock.isContainer())
			"
			:value="blockStyles.fontFamily || 'Inter'"
			@update-value="(val) => setFont(val)">
			Family
		</InlineInput>
		<InlineInput
			v-if="
				store.builderState.selectedBlock &&
				(store.builderState.selectedBlock.isText() || store.builderState.selectedBlock.isContainer())
			"
			:value="blockStyles.fontWeight"
			type="select"
			:options="getFontWeightOptions(blockStyles.fontFamily)"
			@update-value="(val) => (blockStylesObj.fontWeight = val)">
			Weight
		</InlineInput>
		<InlineInput
			v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
			:value="blockStyles.lineHeight"
			@update-value="(val) => (blockStylesObj.lineHeight = val)">
			Line
		</InlineInput>
		<InlineInput
			v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isLink()"
			:value="store.builderState.selectedBlock.attributes.href"
			@update-value="(val) => (store.builderState.selectedBlock.attributes.href = val)">
			Link
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
			v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isButton()"
			:value="store.builderState.selectedBlock.attributes.onclick"
			@update-value="(val) => (store.builderState.selectedBlock.attributes.onclick = val)">
			Action
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
			@update-value="(val) => (blockStylesObj.gridTemplateRows = val)">
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
			@update-value="(val) => (blockStylesObj.gridTemplateColumns = val)">
			Columns
		</InlineInput>
		<InlineInput
			v-if="
				store.builderState.selectedBlock &&
				store.builderState.selectedBlock.isContainer() &&
				blockStyles.display === 'grid'
			"
			:value="blockStyles.gridGap"
			@update-value="(val) => (blockStylesObj.gridGap = val)">
			Gap
		</InlineInput>
		<InlineInput
			v-if="
				store.builderState.selectedBlock &&
				store.builderState.selectedBlock.isContainer() &&
				blockStyles.display === 'grid'
			"
			:value="blockStyles.gridRowGap"
			@update-value="(val) => (blockStylesObj.gridRowGap = val)">
			Row Gap
		</InlineInput>
		<!-- overflow -->
		<InlineInput
			v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer()"
			type="select"
			:options="['visible', 'hidden', 'scroll']"
			:value="blockStyles.overflow"
			@update-value="(val) => (blockStyles.overflow = val)">
			Overflow
		</InlineInput>

		<h3 v-if="store.builderState.selectedBlock" class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">
			RAW Styles
		</h3>
		<Input
			type="textarea"
			class="rounded-md text-sm text-gray-800 dark:bg-zinc-800 dark:text-zinc-200 dark:focus:bg-zinc-700"
			:modelValue="JSON.stringify(store.builderState.selectedBlock.rawStyles, null, 2)"
			@update:modelValue="(val) => (store.builderState.selectedBlock.rawStyles = JSON.parse(val))" />
	</div>
</template>
<script setup>
import useStore from "@/store";
import { setFont as _setFont, fontListNames, getFontWeightOptions } from "@/utils/fontManager";
import { Input } from "frappe-ui";
import { computed } from "vue";
import InlineInput from "./InlineInput.vue";

const store = useStore();

// TODO: Temporary for correctness, remove when we have a better way to handle this
const blockStylesObj = computed(() => {
	let styleObj = store.builderState.selectedBlock.baseStyles;
	if (store.builderState.activeBreakpoint === "mobile") {
		styleObj = store.builderState.selectedBlock.mobileStyles;
	} else if (store.builderState.activeBreakpoint === "tablet") {
		styleObj = store.builderState.selectedBlock.tabletStyles;
	}
	return styleObj;
});

const blockStyles = computed(() => {
	let styleObj = store.builderState.selectedBlock.baseStyles;
	if (store.builderState.activeBreakpoint === "mobile") {
		styleObj = { ...styleObj, ...store.builderState.selectedBlock.mobileStyles };
	} else if (store.builderState.activeBreakpoint === "tablet") {
		styleObj = { ...styleObj, ...store.builderState.selectedBlock.tabletStyles };
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

const setFont = (font) => {
	_setFont(font.value).then(() => {
		store.builderState.selectedBlock.setStyle("fontFamily", font.value);
	});
};
</script>
