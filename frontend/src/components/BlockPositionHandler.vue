<template>
	<div class="flex w-full flex-col gap-4">
		<StylePropertyControl
			propertyKey="position"
			type="select"
			:getModelValue="() => position"
			:setModelValue="setPosition"
			defaultValue="static"
			:enableStates="false"
			:options="[
				{ label: __('Auto'), value: 'static' },
				{ label: __('Free'), value: 'absolute' },
				{ label: __('Relative'), value: 'relative' },
				{
					label: __('Fixed'),
					value: 'fixed',
				},
				{ label: __('Sticky'), value: 'sticky' },
			]"></StylePropertyControl>
		<PositionPins v-if="position === 'absolute' || position === 'fixed'" :fixed="position === 'fixed'" />
		<StickyOffsets v-else-if="position === 'sticky'" />
	</div>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import PositionPins from "@/components/PositionPins.vue";
import StickyOffsets from "@/components/StickyOffsets.vue";
import blockController from "@/utils/blockController";
import BlockPosition from "@/utils/blockPosition";
import { computed } from "vue";

const position = computed(() => (blockController.getStyle("position") as string) || "static");

const setPosition = (value: string | number | boolean) => {
	if (typeof value === "string") {
		new BlockPosition(blockController.getFirstSelectedBlock()).setType(value);
	}
};
</script>
