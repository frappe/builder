<template>
	<h3 class="text-xs font-bold uppercase text-gray-600">Layout</h3>
	<InlineInput
		v-if="block.isContainer()"
		:modelValue="blockStyles.display || 'block'"
		type="select"
		:options="[
			{ label: 'Block', value: 'block' },
			{ label: 'Stack', value: 'flex' },
			{ label: 'Grid', value: 'grid' },
		]"
		@update:modelValue="setLayout">
		Type
	</InlineInput>
	<InlineInput
		v-if="block.isContainer() && blockStyles.display === 'flex'"
		:modelValue="blockStyles.flexDirection"
		type="select"
		:options="[
			{ label: 'Horizontal', value: 'row' },
			{ label: 'Vertical', value: 'column' },
		]"
		default="column"
		@update:modelValue="(val: string | number) => (blockStylesObj.flexDirection = val)">
		Direction
	</InlineInput>
	<InlineInput
		v-if="block.isContainer() && blockStyles.display === 'flex'"
		:modelValue="blockStyles.justifyContent"
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
		@update:modelValue="(val: string | number) => (blockStylesObj.justifyContent = val)">
		Distribute
	</InlineInput>
	<InlineInput
		v-if="block.isContainer() && blockStyles.display === 'flex'"
		:modelValue="blockStyles.alignItems"
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
		@update:modelValue="(val: string | number) => (blockStylesObj.alignItems = val)">
		Align
	</InlineInput>
	<InlineInput
		v-if="block.isContainer() && blockStyles.display === 'flex'"
		:modelValue="blockStyles.flexWrap || 'nowrap'"
		type="select"
		:options="[
			{ label: 'No Wrap', value: 'nowrap' },
			{ label: 'Wrap', value: 'wrap' },
		]"
		default="wrap"
		@update:modelValue="(val: string | number) => (blockStylesObj.flexWrap = val)">
		Wrap
	</InlineInput>
	<InlineInput
		v-if="block.isContainer() && blockStyles.display === 'flex'"
		type="text"
		:modelValue="blockStyles.gap"
		@update:modelValue="(val: string | number) => (blockStylesObj.gap = val)">
		Gap
	</InlineInput>
	<!-- flex basis -->
	<InlineInput
		v-if="block.isContainer() && blockStyles.display === 'flex'"
		type="text"
		:modelValue="blockStyles.flexBasis"
		@update:modelValue="(val: string | number) => (blockStylesObj.flexBasis = val)">
		Basis
	</InlineInput>
	<div class="mt-2 flex flex-col" v-show="block.getParentBlock()?.getStyle('display') === 'flex'">
		<InlineInput
			type="select"
			:options="[
				{
					value: 'row',
					label: 'Row',
				},
				{
					value: 'column',
					label: 'Column',
				},
			]"
			:modelValue="block.getParentBlock()?.getStyle('flexDirection')"
			@update:modelValue="(val) => block.getParentBlock()?.setStyle('flexDirection', val)">
			Arrangement
		</InlineInput>
	</div>
	<div class="flex flex-col" v-show="block.getParentBlock()?.getStyle('display') === 'flex'">
		<InlineInput
			type="select"
			:options="[
				{
					value: 'top-left',
					label: 'Top Left',
				},
				{
					value: 'top-middle',
					label: block.getParentBlock()?.getStyle('flexDirection') === 'row' ? 'Top Middle' : 'Left Middle',
				},
				{
					value: 'top-right',
					label: block.getParentBlock()?.getStyle('flexDirection') === 'row' ? 'Top Right' : 'Bottom Left',
				},
				{
					value: 'middle-left',
					label: block.getParentBlock()?.getStyle('flexDirection') === 'row' ? 'Left Middle' : 'Top Middle',
				},
				{
					value: 'middle-middle',
					label: 'Center',
				},
				{
					value: 'middle-right',
					label:
						block.getParentBlock()?.getStyle('flexDirection') === 'row' ? 'Right Middle' : 'Bottom Middle',
				},
				{
					value: 'bottom-left',
					label: block.getParentBlock()?.getStyle('flexDirection') === 'row' ? 'Bottom Left' : 'Top Right',
				},
				{
					value: 'bottom-middle',
					label:
						block.getParentBlock()?.getStyle('flexDirection') === 'row' ? 'Bottom Middle' : 'Right Middle',
				},
				{
					value: 'bottom-right',
					label: 'Bottom Right',
				},
			]"
			@update:modelValue="setAlignment">
			Placement
		</InlineInput>
	</div>
	<div class="mb-10"></div>
</template>
<script lang="ts" setup>
import Block from "@/utils/block";
import { computed } from "vue";
import InlineInput from "./InlineInput.vue";
import useStore from "@/store";

const store = useStore();

const props = defineProps<{
	block: Block;
}>();

// TODO: Temporary for correctness, remove when we have a better way to handle this
const blockStylesObj = computed(() => {
	let styleObj = props.block.baseStyles;
	if (store.builderState.activeBreakpoint === "mobile") {
		styleObj = props.block.mobileStyles;
	} else if (store.builderState.activeBreakpoint === "tablet") {
		styleObj = props.block.tabletStyles;
	}
	return styleObj;
});

const blockStyles = computed(() => {
	let styleObj = props.block.baseStyles;
	if (store.builderState.activeBreakpoint === "mobile") {
		styleObj = { ...styleObj, ...props.block.mobileStyles };
	} else if (store.builderState.activeBreakpoint === "tablet") {
		styleObj = { ...styleObj, ...props.block.tabletStyles };
	}
	return styleObj;
});

const setLayout = (layout: string) => {
	const { block } = props;
	block.setStyle("display", layout);
	if (layout === "flex") {
		block.setStyle("flexDirection", block.getStyle("flexDirection") || "row");
		block.setStyle("flexWrap", block.getStyle("flexWrap") || "wrap");
		block.setStyle("justifyContent", block.getStyle("justifyContent") || "flex-start");
		block.setStyle("alignItems", block.getStyle("alignItems") || "flex-start");
	} else if (layout === "grid") {
		// block.setStyle("gridTemplateColumns", "repeat(3, 1fr)");
		// block.setStyle("gridTemplateRows", "repeat(3, 1fr)");
		// block.setStyle("gridGap", "10px");
	}
};

const setAlignment = (alignment: string) => {
	const block = props.selectedBlock;
	if (!block) {
		return;
	}
	const parentBlock = block.getParentBlock();

	if (!parentBlock) {
		return;
	}
	if (alignment === "top-right") {
		parentBlock.setStyle("justifyContent", "flex-end");
		parentBlock.setStyle("alignItems", "flex-start");
		parentBlock.setStyle("display", "flex");
	} else if (alignment === "top-middle") {
		parentBlock.setStyle("justifyContent", "center");
		parentBlock.setStyle("alignItems", "flex-start");
		parentBlock.setStyle("display", "flex");
	} else if (alignment === "top-left") {
		parentBlock.setStyle("justifyContent", "flex-start");
		parentBlock.setStyle("alignItems", "flex-start");
		parentBlock.setStyle("display", "flex");
	} else if (alignment === "middle-right") {
		parentBlock.setStyle("alignItems", "center");
		parentBlock.setStyle("justifyContent", "flex-end");
		parentBlock.setStyle("display", "flex");
	} else if (alignment === "middle-middle") {
		parentBlock.setStyle("alignItems", "center");
		parentBlock.setStyle("justifyContent", "center");
		parentBlock.setStyle("display", "flex");
	} else if (alignment === "middle-left") {
		parentBlock.setStyle("alignItems", "center");
		parentBlock.setStyle("justifyContent", "flex-start");
		parentBlock.setStyle("display", "flex");
	} else if (alignment === "bottom-right") {
		parentBlock.setStyle("alignItems", "flex-end");
		parentBlock.setStyle("justifyContent", "flex-end");
		parentBlock.setStyle("display", "flex");
	} else if (alignment === "bottom-middle") {
		parentBlock.setStyle("alignItems", "flex-end");
		parentBlock.setStyle("justifyContent", "center");
		parentBlock.setStyle("display", "flex");
	} else if (alignment === "bottom-left") {
		parentBlock.setStyle("alignItems", "flex-end");
		parentBlock.setStyle("justifyContent", "flex-start");
		parentBlock.setStyle("display", "flex");
	} else if (alignment === "left") {
		parentBlock.setStyle("alignItems", "flex-start");
		parentBlock.setStyle("display", "flex");
	} else if (alignment === "right") {
		parentBlock.setStyle("alignItems", "flex-end");
		parentBlock.setStyle("display", "flex");
	} else if (alignment === "center") {
		parentBlock.setStyle("alignItems", "center");
		parentBlock.setStyle("display", "flex");
	} else if (alignment === "top") {
		parentBlock.setStyle("justifyContent", "flex-start");
		parentBlock.setStyle("display", "flex");
	} else if (alignment === "bottom") {
		parentBlock.setStyle("justifyContent", "flex-end");
		parentBlock.setStyle("display", "flex");
	}
};
</script>
