<template>
	<StylePropertyControl
		propertyKey="flexDirection"
		defaultValue="row"
		:component="OptionToggle"
		:label="__('Direction')"
		v-if="blockController.isFlex()"
		:options="[
			{ label: __('Horizontal'), value: 'row', icon: 'lucide-arrow-right', hideLabel: true },
			{ label: __('Vertical'), value: 'column', icon: 'lucide-arrow-down', hideLabel: true },
		]"></StylePropertyControl>
	<StylePropertyControl
		propertyKey="alignItems"
		:label="__('Placement')"
		:enableStates="false"
		v-if="blockController.isFlex()"
		:component="PlacementControl"></StylePropertyControl>
	<StylePropertyControl
		v-if="blockController.isFlex()"
		propertyKey="justifyContent"
		type="select"
		:label="__('Distribution')"
		:options="[
			{ label: __('Space Between'), value: 'space-between' },
			{ label: __('Space Around'), value: 'space-around' },
			{ label: __('Space Evenly'), value: 'space-evenly' },
		]" />
	<SplitPropertyControl v-if="blockController.isFlex()" v-bind="gapProps" />
	<StylePropertyControl
		propertyKey="flexWrap"
		:component="OptionToggle"
		:label="__('Wrap')"
		v-if="blockController.isFlex()"
		:options="[
			{ label: __('No Wrap'), value: 'nowrap' },
			{ label: __('Wrap'), value: 'wrap' },
		]"
		defaultValue="nowrap"></StylePropertyControl>
	<div class="flex flex-col gap-3" v-if="blockController.getParentBlock()?.isFlex()">
		<StylePropertyControl
			:label="__('Grow')"
			propertyKey="flexGrow"
			:component="OptionToggle"
			:options="[
				{ label: __('Yes'), value: 1 },
				{ label: __('No'), value: 0 },
			]"
			:defaultValue="0" />
		<StylePropertyControl
			:label="__('Shrink')"
			propertyKey="flexShrink"
			:component="OptionToggle"
			:options="[
				{ label: __('Yes'), value: 1 },
				{ label: __('No'), value: 0 },
			]"
			:defaultValue="1" />
		<StylePropertyControl
			:label="__('Order')"
			propertyKey="order"
			:enableSlider="true"
			:min="-99"
			:max="99"
			:step="1"
			:defaultValue="0" />
	</div>
</template>
<script lang="ts" setup>
import { __ } from "@/translation";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import SplitPropertyControl from "@/components/Controls/SplitPropertyControl.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import PlacementControl from "./PlacementControl.vue";

defineProps<{ gapProps: InstanceType<typeof SplitPropertyControl>["$props"] }>();
</script>
