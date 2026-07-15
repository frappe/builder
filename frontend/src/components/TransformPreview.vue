<template>
	<Teleport to="body">
		<span
			class="pointer-events-none fixed z-[1000] flex h-8 items-center justify-center whitespace-nowrap rounded-full bg-gray-600 p-2 text-sm text-white opacity-80"
			:class="wide ? 'w-20' : 'w-fit'"
			:style="previewStyle">
			<slot />
		</span>
	</Teleport>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
	position: { x: number; y: number };
	wide?: boolean;
}>();

const previewStyle = computed(() => ({
	left: `${props.position.x + 12}px`,
	top: `${props.position.y + 12}px`,
}));
</script>
