<template>
	<OptionToggle
		label="Direction"
		v-if="blockController.isFlex()"
		:options="[
			{ label: 'Horizontal', value: 'row', icon: 'arrow-right', hideLabel: true },
			{ label: 'Vertical', value: 'column', icon: 'arrow-down', hideLabel: true },
		]"
		:modelValue="blockController.getStyle('flexDirection') || 'column'"
		@update:modelValue="
			(val: string | number) => blockController.setStyle('flexDirection', val)
		"></OptionToggle>
	<PlacementControl v-if="blockController.isFlex()"></PlacementControl>
	<InlineInput
		v-if="blockController.isFlex()"
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
		v-if="blockController.isFlex()"
		type="text"
		:enableSlider="true"
		:unitOptions="['px', 'em', 'rem']"
		:modelValue="blockController.getStyle('gap')"
		@update:modelValue="(val: string | number) => blockController.setStyle('gap', val)" />
	<OptionToggle
		label="Wrap"
		v-if="blockController.isFlex()"
		:options="[
			{ label: 'No Wrap', value: 'nowrap' },
			{ label: 'Wrap', value: 'wrap' },
		]"
		:modelValue="blockController.getStyle('flexWrap') || 'nowrap'"
		@update:modelValue="(val: string | number) => blockController.setStyle('flexWrap', val)"></OptionToggle>
	<!-- flex basis -->
	<!-- <div class="flex flex-col gap-3" v-if="blockController.getParentBlock()?.isFlex()">
		<InlineInput
			label="Order"
			type="number"
			min="0"
			:modelValue="blockController.getStyle('order')"
			@update:modelValue="(val: string | number) => blockController.setStyle('order', val)" />
	</div> -->
</template>
<script lang="ts" setup>
import blockController from "@/utils/blockController";
import InlineInput from "./InlineInput.vue";
import OptionToggle from "./OptionToggle.vue";
import PlacementControl from "./PlacementControl.vue";
</script>
