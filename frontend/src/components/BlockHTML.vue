<template>
	<div ref="component" class="!relative" v-html="html"></div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import { computed, ref } from "vue";

const component = ref<HTMLElement | null>(null);
const props = defineProps<{
	block: Block;
	data?: Record<string, unknown> | null;
}>();

const html = computed(
	() => `
		<div class="absolute top-0 bottom-0 right-0 left-0"></div>
		${props.block.getInnerHTML()}
	`,
);

defineExpose({
	component,
});
</script>
