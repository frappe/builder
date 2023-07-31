<template>
	<div class="flex flex-col gap-3">
		<h3 class="mb-1 text-xs font-bold uppercase text-gray-600">Layout</h3>
		<div class="flex flex-col" v-show="blockController.getParentBlock()?.getStyle('display') === 'flex'">
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
				:modelValue="blockController.getParentBlock()?.getStyle('flexDirection')"
				@update:modelValue="(val) => blockController.getParentBlock()?.setStyle('flexDirection', val)">
				Arrangement
			</InlineInput>
		</div>
		<div class="flex flex-col" v-show="blockController.getParentBlock()?.getStyle('display') === 'flex'">
			<InlineInput
				type="select"
				:options="[
					{
						value: 'top-left',
						label: 'Top Left',
					},
					{
						value: 'top-middle',
						label:
							blockController.getParentBlock()?.getStyle('flexDirection') === 'row'
								? 'Top Middle'
								: 'Left Middle',
					},
					{
						value: 'top-right',
						label:
							blockController.getParentBlock()?.getStyle('flexDirection') === 'row'
								? 'Top Right'
								: 'Bottom Left',
					},
					{
						value: 'middle-left',
						label:
							blockController.getParentBlock()?.getStyle('flexDirection') === 'row'
								? 'Left Middle'
								: 'Top Middle',
					},
					{
						value: 'middle-middle',
						label: 'Center',
					},
					{
						value: 'middle-right',
						label:
							blockController.getParentBlock()?.getStyle('flexDirection') === 'row'
								? 'Right Middle'
								: 'Bottom Middle',
					},
					{
						value: 'bottom-left',
						label:
							blockController.getParentBlock()?.getStyle('flexDirection') === 'row'
								? 'Bottom Left'
								: 'Top Right',
					},
					{
						value: 'bottom-middle',
						label:
							blockController.getParentBlock()?.getStyle('flexDirection') === 'row'
								? 'Bottom Middle'
								: 'Right Middle',
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

		<div class="flex items-center justify-between">
			<span class="inline-block text-[10px] font-medium uppercase text-gray-600 dark:text-zinc-400">
				Type
			</span>
			<TabButtons
				:modelValue="blockController.getStyle('display') || 'block'"
				:buttons="[
					{ label: 'Block', value: 'block' },
					{ label: 'Stack', value: 'flex' },
				]"
				@update:modelValue="setLayout"
				class="w-fit self-end"></TabButtons>
		</div>
		<InlineInput
			v-if="blockController.getStyle('display') === 'flex'"
			:modelValue="blockController.getStyle('flexDirection')"
			type="select"
			:options="[
				{ label: 'Horizontal', value: 'row' },
				{ label: 'Vertical', value: 'column' },
			]"
			default="column"
			@update:modelValue="(val: string | number) => blockController.setStyle('flexDirection', val)">
			Direction
		</InlineInput>
		<InlineInput
			v-if="blockController.getStyle('display') === 'flex'"
			:modelValue="blockController.getStyle('justifyContent')"
			type="select"
			:options="[
				{
					label: blockController.getStyle('flexDirection') === 'row' ? 'Start' : 'Top',
					value: 'flex-start',
				},
				{
					label: blockController.getStyle('flexDirection') === 'row' ? 'Center' : 'Middle',
					value: 'center',
				},
				{
					label: blockController.getStyle('flexDirection') === 'row' ? 'End' : 'Bottom',
					value: 'flex-end',
				},
				{ label: 'Space Between', value: 'space-between' },
				{ label: 'Space Around', value: 'space-around' },
				{ label: 'Space Evenly', value: 'space-evenly' },
			]"
			@update:modelValue="(val: string | number) => blockController.setStyle('justifyContent', val)">
			Distribute
		</InlineInput>
		<InlineInput
			v-if="blockController.getStyle('display') === 'flex'"
			:modelValue="blockController.getStyle('alignItems')"
			type="select"
			:options="[
				{
					label: blockController.getStyle('flexDirection') === 'column' ? 'Start' : 'Top',
					value: 'flex-start',
				},
				{
					label: blockController.getStyle('flexDirection') === 'column' ? 'Center' : 'Middle',
					value: 'center',
				},
				{
					label: blockController.getStyle('flexDirection') === 'column' ? 'End' : 'Bottom',
					value: 'flex-end',
				},
			]"
			@update:modelValue="(val: string | number) => blockController.setStyle('alignItems', val)">
			Align
		</InlineInput>
		<div class="flex items-center justify-between" v-if="blockController.getStyle('display') === 'flex'">
			<span class="inline-block text-[10px] font-medium uppercase text-gray-600 dark:text-zinc-400">
				Wrap
			</span>
			<TabButtons
				:modelValue="blockController.getStyle('flexWrap') || 'nowrap'"
				:buttons="[
					{ label: 'No Wrap', value: 'nowrap' },
					{ label: 'Wrap', value: 'wrap' },
				]"
				@update:modelValue="(val: string | number) => blockController.setStyle('flexWrap', val)"
				class="w-fit self-end"></TabButtons>
		</div>
		<InlineInput
			v-if="blockController.getStyle('display') === 'flex'"
			type="text"
			:modelValue="blockController.getStyle('gap')"
			@update:modelValue="(val: string | number) => blockController.setStyle('gap', val)">
			Gap
		</InlineInput>
		<!-- flex basis -->
		<InlineInput
			v-if="blockController.getStyle('display') === 'flex'"
			type="text"
			:modelValue="blockController.getStyle('flexBasis')"
			@update:modelValue="(val: string | number) => blockController.setStyle('flexBasis', val)">
			Basis
		</InlineInput>
		<InlineInput
			v-if="blockController.getStyle('display') === 'flex'"
			type="text"
			:modelValue="blockController.getStyle('flexGrow')"
			@update:modelValue="(val: string | number) => blockController.setStyle('flexGrow', val)">
			Grow
		</InlineInput>
	</div>
</template>
<script lang="ts" setup>
import blockController from "@/utils/blockController";
import { TabButtons } from "frappe-ui";
import InlineInput from "./InlineInput.vue";

const setLayout = (layout: string) => {
	blockController.setStyle("display", layout);
	if (layout === "flex") {
		blockController.setStyle("flexDirection", blockController.getStyle("flexDirection") || "row");
		blockController.setStyle("flexWrap", blockController.getStyle("flexWrap") || "nowrap");
		blockController.setStyle("justifyContent", blockController.getStyle("justifyContent") || "flex-start");
		blockController.setStyle("alignItems", blockController.getStyle("alignItems") || "flex-start");
	}
};

const setAlignment = (alignment: string) => {
	const parentBlock = blockController.getParentBlock();

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
