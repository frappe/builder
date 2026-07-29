<template>
	<div
		ref="component"
		:class="{
			'!relative': !block.getStyle('position') || block.getStyle('position') === 'static',
		}"
		v-html="html"></div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import { BlockValueResolver } from "@/utils/blockValueResolver";
import { computed, ref } from "vue";

const component = ref<HTMLElement | null>(null);
const props = defineProps<{
	block: Block;
	data?: Record<string, unknown> | null;
	componentData?: Record<string, unknown> | null;
	defaultProps?: BlockProps | null;
}>();

const valueResolver = new BlockValueResolver({
	block: () => props.block,
	data: () => props.data ?? null,
	componentData: () => props.componentData ?? null,
	defaultProps: () => props.defaultProps ?? null,
});

const html = computed(() => {
	let content = props.block.getInnerHTML();
	const dynamicContent = valueResolver.applyDynamicValues("key", { innerHTML: null }).innerHTML;
	if (dynamicContent) {
		content = dynamicContent;
	}
	return `
		<div class="absolute top-0 bottom-0 right-0 left-0"></div>
		${content}
	`;
});

defineExpose({
	component,
});
</script>
