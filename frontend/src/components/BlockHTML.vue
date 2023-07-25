<template>
	<div v-html="block.innerHTML" ref="component"></div>
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
});

defineExpose({
	component,
});
</script>
