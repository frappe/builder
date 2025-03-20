<template>
	<div ref="component" class="!relative">
		<slot />
	</div>
</template>
<script setup lang="ts">
import Block from "@/block";
import { ref } from "vue";

const component = ref<HTMLElement | null>(null);
defineProps({
	block: {
		type: Block,
		required: true,
	},
	data: {
		type: Object,
		default: null,
	},
});

defineExpose({
	component,
});
</script>
