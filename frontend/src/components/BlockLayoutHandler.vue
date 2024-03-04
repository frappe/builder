<!-- TODO: Refactor -->
<template>
	<div class="flex items-center justify-between" v-if="blockController.getStyle('display') === 'flex'">
		<span class="inline-block text-[10px] font-medium uppercase text-gray-600 dark:text-zinc-400">
			Direction
		</span>
		<TabButtons
			:modelValue="blockController.getStyle('flexDirection') || 'column'"
			:buttons="[
				{ label: 'Horizontal', value: 'row' },
				{ label: 'Vertical', value: 'column' },
			]"
			@update:modelValue="(val: string | number) => blockController.setStyle('flexDirection', val)"
			class="w-fit self-end [&>div>button[aria-checked='false']]:dark:!bg-transparent [&>div>button[aria-checked='false']]:dark:!text-zinc-400 [&>div>button[aria-checked='true']]:dark:!bg-zinc-700 [&>div>button]:dark:!bg-zinc-700 [&>div>button]:dark:!text-zinc-100 [&>div]:dark:!bg-zinc-800"></TabButtons>
	</div>
	<div class="items-top relative flex justify-between" v-if="blockController.getStyle('display') === 'flex'">
		<span class="inline-block text-[10px] font-medium uppercase text-gray-600 dark:text-zinc-400">
			Placement
		</span>
		<div
			class="grid h-16 w-16 grid-cols-3 items-center justify-items-center rounded-sm bg-gray-200 p-1 dark:bg-zinc-800">
			<div
				class="h-3 w-3 cursor-pointer rounded-sm bg-gray-300 hover:bg-gray-400 dark:bg-zinc-700 dark:hover:bg-zinc-600"
				:class="{
					'bg-gray-700 dark:!bg-zinc-500': activePlacement === option,
				}"
				v-for="option in placementOptions"
				:key="option"
				@click="setAlignment(option)"></div>
		</div>
	</div>

	<InlineInput
		v-if="blockController.getStyle('display') === 'flex'"
		:modelValue="blockController.getStyle('justifyContent')"
		type="select"
		label="Arrangement"
		:options="[
			{ label: 'Space Between', value: 'space-between' },
			{ label: 'Space Around', value: 'space-around' },
			{ label: 'Space Evenly', value: 'space-evenly' },
		]"
		@update:modelValue="(val: string | number) => blockController.setStyle('justifyContent', val)" />

	<InlineInput
		label="Gap"
		v-if="blockController.getStyle('display') === 'flex'"
		type="text"
		:enableSlider="true"
		:unitOptions="['px', 'em', 'rem']"
		:modelValue="blockController.getStyle('gap')"
		@update:modelValue="(val: string | number) => blockController.setStyle('gap', val)" />

	<div class="flex items-center justify-between" v-if="blockController.getStyle('display') === 'flex'">
		<span class="inline-block text-[10px] font-medium uppercase text-gray-600 dark:text-zinc-400">Wrap</span>
		<TabButtons
			:modelValue="blockController.getStyle('flexWrap') || 'nowrap'"
			:buttons="[
				{ label: 'No Wrap', value: 'nowrap' },
				{ label: 'Wrap', value: 'wrap' },
			]"
			@update:modelValue="(val: string | number) => blockController.setStyle('flexWrap', val)"
			class="w-fit self-end [&>div>button[aria-checked='false']]:dark:!bg-transparent [&>div>button[aria-checked='false']]:dark:!text-zinc-400 [&>div>button[aria-checked='true']]:dark:!bg-zinc-700 [&>div>button]:dark:!bg-zinc-700 [&>div>button]:dark:!text-zinc-100 [&>div]:dark:!bg-zinc-800"></TabButtons>
	</div>
	<!-- flex basis -->
	<div class="flex flex-col gap-3" v-if="blockController.getParentBlock()?.isFlex()">
		<InlineInput
			label="Basis"
			type="text"
			:enableSlider="true"
			:unitOptions="['px', 'em', 'rem']"
			:modelValue="blockController.getStyle('flexBasis')"
			@update:modelValue="(val: string | number) => blockController.setStyle('flexBasis', val)" />
		<div class="flex items-center justify-between">
			<span class="inline-block text-[10px] font-medium uppercase text-gray-600 dark:text-zinc-400">
				Grow
			</span>
			<TabButtons
				label="Grow"
				:modelValue="blockController.getStyle('flexGrow') || 0"
				:buttons="[
					{ label: 'Yes', value: 1 },
					{ label: 'No', value: 0 },
				]"
				@update:modelValue="(val: string | number) => blockController.setStyle('flexGrow', val)"
				class="w-fit self-end [&>div>button[aria-checked='false']]:dark:!bg-transparent [&>div>button[aria-checked='false']]:dark:!text-zinc-400 [&>div>button[aria-checked='true']]:dark:!bg-zinc-700 [&>div>button]:dark:!bg-zinc-700 [&>div>button]:dark:!text-zinc-100 [&>div]:dark:!bg-zinc-800"></TabButtons>
		</div>
		<div class="flex items-center justify-between">
			<span class="inline-block text-[10px] font-medium uppercase text-gray-600 dark:text-zinc-400">
				Shrink
			</span>
			<TabButtons
				label="Shrink"
				:modelValue="
					blockController.getStyle('flexShrink') === undefined ? 1 : blockController.getStyle('flexShrink')
				"
				:buttons="[
					{ label: 'Yes', value: 1 },
					{ label: 'No', value: 0 },
				]"
				@update:modelValue="(val: string | number) => blockController.setStyle('flexShrink', val)"
				class="w-fit self-end [&>div>button[aria-checked='false']]:dark:!bg-transparent [&>div>button[aria-checked='false']]:dark:!text-zinc-400 [&>div>button[aria-checked='true']]:dark:!bg-zinc-700 [&>div>button]:dark:!bg-zinc-700 [&>div>button]:dark:!text-zinc-100 [&>div]:dark:!bg-zinc-800"></TabButtons>
		</div>
		<InlineInput
			label="Order"
			type="number"
			min="0"
			:modelValue="blockController.getStyle('order')"
			@update:modelValue="(val: string | number) => blockController.setStyle('order', val)" />
	</div>
</template>
<script lang="ts" setup>
import blockController from "@/utils/blockController";
import { TabButtons } from "frappe-ui";
import { computed } from "vue";
import InlineInput from "./InlineInput.vue";

const placementOptions = [
	"top-left",
	"top-middle",
	"top-right",
	"middle-left",
	"middle-middle",
	"middle-right",
	"bottom-left",
	"bottom-middle",
	"bottom-right",
];

const activePlacement = computed(() => {
	return placementOptions.filter((option) => {
		const flexDirection = blockController.getStyle("flexDirection");
		const justifyContent = blockController.getStyle("justifyContent");
		const alignItems = blockController.getStyle("alignItems");
		switch (option) {
			case "top-left":
				return justifyContent === "flex-start" && alignItems === "flex-start";
			case "top-middle":
				return (
					(flexDirection === "row" && justifyContent === "center" && alignItems === "flex-start") ||
					(flexDirection === "column" && justifyContent === "flex-start" && alignItems === "center")
				);
			case "top-right":
				return (
					(flexDirection === "row" && justifyContent === "flex-end" && alignItems === "flex-start") ||
					(flexDirection === "column" && justifyContent === "flex-start" && alignItems === "flex-end")
				);
			case "middle-left":
				return (
					(flexDirection === "row" && justifyContent === "flex-start" && alignItems === "center") ||
					(flexDirection === "column" && justifyContent === "center" && alignItems === "flex-start")
				);
			case "middle-middle":
				return justifyContent === "center" && alignItems === "center";
			case "middle-right":
				return (
					(flexDirection === "row" && justifyContent === "flex-end" && alignItems === "center") ||
					(flexDirection === "column" && justifyContent === "center" && alignItems === "flex-end")
				);
			case "bottom-left":
				return (
					(flexDirection === "row" && justifyContent === "flex-start" && alignItems === "flex-end") ||
					(flexDirection === "column" && justifyContent === "flex-end" && alignItems === "flex-start")
				);
			case "bottom-middle":
				return (
					(flexDirection === "row" && justifyContent === "center" && alignItems === "flex-end") ||
					(flexDirection === "column" && justifyContent === "flex-end" && alignItems === "center")
				);
			case "bottom-right":
				return justifyContent === "flex-end" && alignItems === "flex-end";
		}
	})[0];
});

const setAlignment = (alignment: string) => {
	blockController.setStyle("display", "flex");
	const flexDirection = blockController.getStyle("flexDirection");
	switch (alignment) {
		case "top-right":
			if (flexDirection === "row") {
				blockController.setStyle("justifyContent", "flex-end");
				blockController.setStyle("alignItems", "flex-start");
			} else {
				blockController.setStyle("justifyContent", "flex-start");
				blockController.setStyle("alignItems", "flex-end");
			}
			break;
		case "top-middle":
			if (flexDirection === "row") {
				blockController.setStyle("justifyContent", "center");
				blockController.setStyle("alignItems", "flex-start");
			} else {
				blockController.setStyle("justifyContent", "flex-start");
				blockController.setStyle("alignItems", "center");
			}
			break;
		case "top-left":
			blockController.setStyle("justifyContent", "flex-start");
			blockController.setStyle("alignItems", "flex-start");
			break;
		case "middle-right":
			if (flexDirection === "row") {
				blockController.setStyle("justifyContent", "flex-end");
				blockController.setStyle("alignItems", "center");
			} else {
				blockController.setStyle("justifyContent", "center");
				blockController.setStyle("alignItems", "flex-end");
			}
			break;
		case "middle-middle":
			blockController.setStyle("justifyContent", "center");
			blockController.setStyle("alignItems", "center");
			break;
		case "middle-left":
			if (flexDirection === "row") {
				blockController.setStyle("justifyContent", "flex-start");
				blockController.setStyle("alignItems", "center");
			} else {
				blockController.setStyle("justifyContent", "center");
				blockController.setStyle("alignItems", "flex-start");
			}
			break;
		case "bottom-right":
			if (flexDirection === "row") {
				blockController.setStyle("justifyContent", "flex-end");
				blockController.setStyle("alignItems", "flex-end");
			} else {
				blockController.setStyle("justifyContent", "flex-end");
				blockController.setStyle("alignItems", "flex-end");
			}
			break;
		case "bottom-middle":
			if (flexDirection === "row") {
				blockController.setStyle("justifyContent", "center");
				blockController.setStyle("alignItems", "flex-end");
			} else {
				blockController.setStyle("justifyContent", "flex-end");
				blockController.setStyle("alignItems", "center");
			}
			break;
		case "bottom-left":
			if (flexDirection === "row") {
				blockController.setStyle("justifyContent", "flex-start");
				blockController.setStyle("alignItems", "flex-end");
			} else {
				blockController.setStyle("justifyContent", "flex-end");
				blockController.setStyle("alignItems", "flex-start");
			}
			break;
	}
};
</script>
