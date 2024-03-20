<template>
	<div ref="component">
		<div v-html="block.getInnerHTML()" class="pointer-events-none"></div>
	</div>
</template>
<script setup lang="ts">
import Block from "@/utils/block";
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
