<template>
	<StylePropertyControl
		styleProperty="flexDirection"
		defaultValue="row"
		:component="OptionToggle"
		label="Direction"
		v-if="blockController.isFlex()"
		:options="[
			{ label: 'Horizontal', value: 'row', icon: 'arrow-right', hideLabel: true },
			{ label: 'Vertical', value: 'column', icon: 'arrow-down', hideLabel: true },
		]"></StylePropertyControl>
	<StylePropertyControl
		styleProperty="alignItems"
		label="Placement"
		:enableStates="false"
		v-if="blockController.isFlex()"
		:component="PlacementControl"></StylePropertyControl>
	<StylePropertyControl
		v-if="blockController.isFlex()"
		styleProperty="justifyContent"
		type="select"
		label="Distribution"
		:options="[
			{ label: 'Space Between', value: 'space-between' },
			{ label: 'Space Around', value: 'space-around' },
			{ label: 'Space Evenly', value: 'space-evenly' },
		]" />
	<StylePropertyControl
		v-if="blockController.isFlex()"
		label="Gap"
		styleProperty="gap"
		:enableSlider="true"
		:unitOptions="['px', 'em', 'rem']" />
	<StylePropertyControl
		styleProperty="flexWrap"
		:component="OptionToggle"
		label="Wrap"
		v-if="blockController.isFlex()"
		:options="[
			{ label: 'No Wrap', value: 'nowrap' },
			{ label: 'Wrap', value: 'wrap' },
		]"
		defaultValue="nowrap"></StylePropertyControl>
	<div class="flex flex-col gap-3" v-if="blockController.getParentBlock()?.isFlex()">
		<StylePropertyControl
			label="Order"
			styleProperty="order"
			:enableSlider="true"
			:min="-99"
			:max="99"
			:step="1"
			:defaultValue="0" />
		<StylePropertyControl
			label="Grow"
			styleProperty="flexGrow"
			:component="OptionToggle"
			:options="[
				{ label: 'Yes', value: 1 },
				{ label: 'No', value: 0 },
			]"
			:defaultValue="0" />
		<StylePropertyControl
			label="Shrink"
			styleProperty="flexShrink"
			:component="OptionToggle"
			:options="[
				{ label: 'Yes', value: 1 },
				{ label: 'No', value: 0 },
			]"
			:defaultValue="1" />
	</div>
</template>
<script lang="ts" setup>
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import PlacementControl from "./PlacementControl.vue";
</script>
