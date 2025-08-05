<template>
	<div ref="component" class="!relative" v-html="html"></div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import { getDataForKey } from "@/utils/helpers";
import { computed, ref } from "vue";

const component = ref<HTMLElement | null>(null);
const props = defineProps<{
	block: Block;
	data?: Record<string, unknown> | null;
}>();

const getDynamicContent = () => {
	let innerHTML = null as string | null;
	if (props.data && props.block.getDataKey("property") === "innerHTML") {
		const dataValue = getDataForKey(props.data, props.block.getDataKey("key"));
		innerHTML = typeof dataValue === "string" ? dataValue : innerHTML;
	}
	if (props.data) {
		props.block.dynamicValues
			?.filter((dataKeyObj: BlockDataKey) => {
				return dataKeyObj.property === "innerHTML" && dataKeyObj.type === "key";
			})
			?.forEach((dataKeyObj: BlockDataKey) => {
				const dataValue = getDataForKey(props.data as Record<string, any>, dataKeyObj.key as string);
				innerHTML = typeof dataValue === "string" ? dataValue : innerHTML;
			});
	}
	return innerHTML;
};

const html = computed(() => {
	let content = props.block.getInnerHTML();
	if (props.data) {
		const dynamicContent = getDynamicContent();
		if (dynamicContent) {
			content = dynamicContent;
		}
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
