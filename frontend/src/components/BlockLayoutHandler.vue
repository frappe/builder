<!-- TODO: Refactor -->
<template>
	<div class="flex items-center justify-between" v-if="blockController.getStyle('display') === 'flex'">
		<OptionToggle
			:label="'Direction'"
			:modelValue="blockController.getStyle('flexDirection') || 'column'"
			:options="[
				{ label: 'Horizontal', value: 'row' },
				{ label: 'Vertical', value: 'column' },
			]"
			@update:modelValue="
				(val: string | number) => blockController.setStyle('flexDirection', val)
			"></OptionToggle>
	</div>
	<div class="items-top relative flex justify-between" v-if="blockController.getStyle('display') === 'flex'">
		<InputLabel>Placement</InputLabel>
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
		:modelValue="blockController.getStyle('justifyContent') || 'flex-start'"
		type="select"
		label="Arrangement"
		:options="[
			{ label: 'Start', value: 'flex-start' },
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
		:modelValue="blockController.getStyle('gap') || '0'"
		@update:modelValue="(val: string | number) => blockController.setStyle('gap', val)" />

	<div class="flex items-center justify-between" v-if="blockController.getStyle('display') === 'flex'">
		<OptionToggle
			:label="'Wrap'"
			:modelValue="blockController.getStyle('flexWrap') || 'nowrap'"
			:options="[
				{ label: 'No Wrap', value: 'nowrap' },
				{ label: 'Wrap', value: 'wrap' },
			]"
			@update:modelValue="(val: string | number) => blockController.setStyle('flexWrap', val)"></OptionToggle>
	</div>
	<!-- flex basis -->
	<div class="flex flex-col gap-3" v-if="blockController.getParentBlock()?.isFlex()">
		<InlineInput
			label="Basis"
			type="text"
			:enableSlider="true"
			:unitOptions="['px', 'em', 'rem']"
			:modelValue="blockController.getStyle('flexBasis') || 'auto'"
			@update:modelValue="(val: string | number) => blockController.setStyle('flexBasis', val)" />
		<div class="flex items-center justify-between">
			<OptionToggle
				:label="'Grow'"
				:modelValue="blockController.getStyle('flexGrow') || 0"
				:options="[
					{ label: 'Yes', value: 1 },
					{ label: 'No', value: 0 },
				]"
				@update:modelValue="
					(val: string | number) => blockController.setStyle('flexGrow', val)
				"></OptionToggle>
		</div>
		<div class="flex items-center justify-between">
			<OptionToggle
				:label="'Shrink'"
				:modelValue="
					blockController.getStyle('flexShrink') === undefined
						? 1
						: (blockController.getStyle('flexShrink') as number)
				"
				:options="[
					{ label: 'Yes', value: 1 },
					{ label: 'No', value: 0 },
				]"
				@update:modelValue="
					(val: string | number) => blockController.setStyle('flexShrink', val)
				"></OptionToggle>
		</div>
		<InlineInput
			label="Order"
			type="number"
			min="0"
			:modelValue="blockController.getStyle('order') || 0"
			@update:modelValue="(val: string | number) => blockController.setStyle('order', val)" />
	</div>
</template>
<script lang="ts" setup>
import blockController from "@/utils/blockController";
import { computed } from "vue";
import InlineInput from "./InlineInput.vue";
import InputLabel from "./InputLabel.vue";
import OptionToggle from "./OptionToggle.vue";

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
	if (alignment === activePlacement.value) {
		blockController.setStyle("justifyContent", "");
		blockController.setStyle("alignItems", "");
		return;
	}
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
