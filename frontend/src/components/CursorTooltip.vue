<template>
	<Teleport to="body">
		<span
			class="pointer-events-none fixed z-[1000] flex h-8 items-center justify-center whitespace-nowrap rounded-full p-2 text-sm"
			:class="[
				wide ? 'w-20' : 'w-fit',
				purple ? 'bg-purple-100 text-purple-900' : 'bg-gray-600 text-white opacity-80',
			]"
			:style="tooltipStyle">
			<slot />
		</span>
	</Teleport>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
	position: { x: number; y: number };
	wide?: boolean;
	purple?: boolean;
}>();

const tooltipStyle = computed(() => ({
	left: `${props.position.x + 12}px`,
	top: `${props.position.y + 12}px`,
}));
</script>
