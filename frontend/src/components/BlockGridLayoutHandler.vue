<template>
	<StylePropertyControl
		propertyKey="gridTemplateColumns"
		:component="OptionToggle"
		class="w-full"
		:label="__('Grid Type')"
		v-if="blockController.isGrid()"
		:getModelValue="getGridType"
		:setModelValue="setGridType"
		:enableStates="false"
		:options="[
			{ label: __('Fixed'), value: 'fixed' },
			{ label: __('Auto'), value: 'auto' },
		]" />
	<InlineInput
		v-if="blockController.isGrid() && isFixed"
		:label="__('Columns')"
		:modelValue="columns"
		:enableSlider="true"
		:changeFactor="0.08"
		:minValue="1"
		:maxValue="20"
		@update:modelValue="setColumns" />
	<InlineInput
		v-if="blockController.isGrid() && isFixed"
		:label="__('Rows')"
		:modelValue="rows"
		:enableSlider="true"
		:changeFactor="0.08"
		:minValue="1"
		:maxValue="20"
		@update:modelValue="setRows" />
	<InlineInput
		:label="__('Item Width')"
		v-if="blockController.isGrid()"
		v-show="['auto-fit', 'auto-fill'].includes(columns as string)"
		type="text"
		:modelValue="width"
		:enableSlider="true"
		:unitOptions="GRID_UNIT_OPTIONS"
		@update:modelValue="setWidth" />
	<InlineInput
		:label="__('Row Height')"
		v-if="blockController.isGrid()"
		v-show="['auto-fit', 'auto-fill'].includes(rows as string)"
		:enableSlider="true"
		:unitOptions="GRID_UNIT_OPTIONS"
		type="text"
		:modelValue="height"
		@update:modelValue="setHeight" />
	<SplitPropertyControl v-if="blockController.isGrid()" v-bind="gapProps" />
	<!-- <InlineInput
		label="Align"
		v-if="blockController.isGrid()"
		type="select"
		:modelValue="blockController.getStyle('justifyItems') || 'stretch'"
		:options="[
			{
				label: __('Stretch'),
				value: 'stretch',
			},
			{
				label: __('Start'),
				value: 'start',
			},
			{
				label: __('Center'),
				value: 'center',
			},
			{
				label: __('End'),
				value: 'end',
			},
		]"
		@update:modelValue="(val: string) => blockController.setStyle('justifyItems', val)" /> -->
	<!-- <InlineInput
		label="Flow"
		v-if="blockController.isGrid()"
		type="select"
		:modelValue="blockController.getStyle('gridAutoFlow') || 'row'"
		:options="[
			{
				label: __('Row'),
				value: 'row',
			},
			{
				label: __('Column'),
				value: 'column',
			},
			{
				label: __('Row Dense'),
				value: 'row dense',
			},
			{
				label: __('Column Dense'),
				value: 'column dense',
			},
		]"
		@update:modelValue="(val: string) => blockController.setStyle('gridAutoFlow', val)" /> -->

	<!-- place items -->
	<!-- <InlineInput
		label="Place Items"
		v-if="blockController.isGrid()"
		type="select"
		:modelValue="blockController.getStyle('placeItems') || 'stretch'"
		:options="[
			{
				label: __('Top Right'),
				value: 'start end',
			},
			{
				label: __('Top Center'),
				value: 'start center',
			},
			{
				label: __('Top Left'),
				value: 'start start',
			},
			{
				label: __('Center Right'),
				value: 'center end',
			},
			{
				label: __('Center'),
				value: 'center center',
			},
			{
				label: __('Center Left'),
				value: 'center start',
			},
			{
				label: __('Bottom Right'),
				value: 'end end',
			},
			{
				label: __('Bottom Center'),
				value: 'end center',
			},
			{
				label: __('Bottom Left'),
				value: 'end start',
			},
		]"
		@update:modelValue="(val: string) => blockController.setStyle('placeItems', val)" /> -->

	<InlineInput
		:label="__('Col Span')"
		v-if="blockController.getParentBlock()?.isGrid()"
		type="text"
		:enableSlider="true"
		:changeFactor="0.08"
		:modelValue="columnSpan"
		@update:modelValue="setColumnSpan" />
	<InlineInput
		:label="__('Row Span')"
		v-if="blockController.getParentBlock()?.isGrid()"
		type="text"
		:enableSlider="true"
		:changeFactor="0.08"
		:modelValue="rowSpan"
		@update:modelValue="setRowSpan" />

	<!-- place self -->
	<!-- <InlineInput
		label="Place Self"
		v-if="blockController.getParentBlock()?.isGrid()"
		type="select"
		:modelValue="blockController.getStyle('placeSelf') || 'stretch'"
		:options="[
			{
				label: __('Top Right'),
				value: 'start end',
			},
			{
				label: __('Top Center'),
				value: 'start center',
			},
			{
				label: __('Top Left'),
				value: 'start start',
			},
			{
				label: __('Center Right'),
				value: 'center end',
			},
			{
				label: __('Center'),
				value: 'center center',
			},
			{
				label: __('Center Left'),
				value: 'center start',
			},
			{
				label: __('Bottom Right'),
				value: 'end end',
			},
			{
				label: __('Bottom Center'),
				value: 'end center',
			},
			{
				label: __('Bottom Left'),
				value: 'end start',
			},
		]"
		@update:modelValue="(val: string) => blockController.setStyle('placeSelf', val)" /> -->
</template>
<script lang="ts" setup>
import { __ } from "@/translation";
import InlineInput from "@/components/Controls/InlineInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import SplitPropertyControl from "@/components/Controls/SplitPropertyControl.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { GRID_UNIT_OPTIONS } from "@/utils/unitOptions";
import { computed } from "vue";

defineProps<{ gapProps: InstanceType<typeof SplitPropertyControl>["$props"] }>();

const getGridType = () => {
	return isFixed.value ? "fixed" : "auto";
};

const columns = computed(() => {
	const template = blockController.getStyle("gridTemplateColumns") as string;
	if (!template) {
		return;
	}
	const value = parseRepeatFunction(template);
	return value.repeat || 1;
});

const rows = computed(() => {
	const template = blockController.getStyle("gridTemplateRows") as string;
	if (!template) {
		return;
	}
	const value = parseRepeatFunction(template);
	return value.repeat || 1;
});

const width = computed(() => {
	const template = blockController.getStyle("gridTemplateColumns") as string;
	const value = parseRepeatFunction(template);
	return value.minValue !== "0" ? value.minValue : "200px";
});

const height = computed(() => {
	const template = blockController.getStyle("gridTemplateRows") as string;
	const value = parseRepeatFunction(template);
	return value.minValue !== "0" ? value.minValue : "200px";
});

const columnSpan = computed(() => {
	let gridColumn = blockController.getStyle("gridColumn") as string;
	if (!gridColumn) {
		return 1;
	}
	gridColumn = gridColumn.replace("span", "").trim();
	const [start, end] = gridColumn.split("/");
	return end ? parseInt(end) - parseInt(start) : start || 1;
});

const rowSpan = computed(() => {
	let gridRow = blockController.getStyle("gridRow") as string;
	if (!gridRow) {
		return 1;
	}
	gridRow = gridRow.replace("span", "").trim();
	const [start, end] = gridRow.split("/");
	return end ? parseInt(end) - parseInt(start) : start || 1;
});

const setColumns = (val: string | number) => {
	if (val == null) {
		val = "auto-fill";
	}
	const widthRange = `minmax(0, 1fr)`;
	val = `repeat(${val}, ${widthRange})`;
	blockController.setStyle("gridTemplateColumns", val);
	blockController.setStyle("gridAutoColumns", widthRange);
};

const setRows = (val: string | number) => {
	if (val == null) {
		val = "auto-fill";
	}
	const heightRange = `minmax(0, 1fr)`;
	val = `repeat(${val}, ${heightRange})`;
	blockController.setStyle("gridTemplateRows", val);
	blockController.setStyle("gridAutoRows", heightRange);
};

const setWidth = (val: string | number) => {
	if (val == null) {
		val = "1fr";
	}
	const widthRange = `minmax(${val}, 1fr)`;
	val = `repeat(${columns.value}, ${widthRange})`;
	blockController.setStyle("gridTemplateColumns", val);
	blockController.setStyle("gridAutoColumns", widthRange);
};

const setHeight = (val: string | number) => {
	if (val == null) {
		val = "1fr";
	}
	const heightRange = `minmax(${val}, 1fr)`;
	val = `repeat(${rows.value}, ${heightRange})`;
	blockController.setStyle("gridTemplateRows", val);
	blockController.setStyle("gridAutoRows", heightRange);
};

const setColumnSpan = (val: string) => {
	blockController.setStyle("width", null);
	blockController.setStyle("minWidth", null);
	blockController.setStyle("maxWidth", null);

	if (!val) {
		blockController.setStyle("gridColumn", val);
	} else {
		blockController.setStyle("gridColumn", `span ${val}`);
	}
};

const setRowSpan = (val: string) => {
	blockController.setStyle("height", null);
	blockController.setStyle("minHeight", null);
	blockController.setStyle("maxHeight", null);

	if (!val) {
		blockController.setStyle("gridRow", val);
	} else {
		blockController.setStyle("gridRow", `span ${val}`);
	}
};

function parseRepeatFunction(input: string) {
	const res = {
		repeat: 1 as number | string,
		minValue: 0 as number | string,
	};
	if (!input) {
		return res;
	}
	const repeatPattern = /repeat\((\d+|auto-fit|auto-fill),\s*(.+)\)/;
	const minMaxPattern = /minmax\((.+),\s*(.+)\)/;
	const match = input.match(repeatPattern);
	if (match) {
		const countOrKeyword = match[1]; // Extract the count or keyword
		const values = match[2].trim(); // Extract the values inside the repeat
		const minValueMatch = values.match(minMaxPattern);
		res.repeat = isNaN(parseInt(countOrKeyword, 10)) ? countOrKeyword : parseInt(countOrKeyword, 10);
		res.minValue = minValueMatch ? minValueMatch[1] : 0;
	}
	return res;
}

const isFixed = computed(() => {
	const template = blockController.getStyle("gridTemplateColumns") as string;
	if (!template) {
		return false;
	}
	const value = parseRepeatFunction(template);
	return value.repeat !== "auto-fill" && value.repeat !== "auto-fit";
});

const setGridType = (val: string | number | boolean) => {
	if (val === "fixed") {
		blockController.setStyle("gridTemplateColumns", `repeat(2, minmax(0, 1fr))`);
	} else {
		blockController.setStyle("gridTemplateColumns", `repeat(auto-fill, minmax(${width.value}, 1fr))`);
	}
};
</script>
