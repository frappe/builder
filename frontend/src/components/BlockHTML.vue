<template>
	<div ref="component" class="!relative" v-html="html"></div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import { getDataForKey, getPropValue } from "@/utils/helpers";
import { computed, ref } from "vue";

const component = ref<HTMLElement | null>(null);
const props = defineProps<{
	block: Block;
	data?: Record<string, unknown> | null;
	defaultProps?: Record<string, unknown> | null;
}>();

const getDynamicContent = () => {
	let innerHTML = null as string | null;
	if (props.data || props.defaultProps) {
		const data = props.data; // to "freeze" props.data for getDataScriptValue
		const getDataScriptValue = (path: string): any => {
			return getDataForKey(data || {}, path);
		};
		if (props.block.getDataKey("property") === "innerHTML") {
			let value;
			if (props.block.getDataKey("comesFrom") === "props") {
				// props are checked first as unavailablity of comesFrom means it comes from dataScript (legacy)
				value = getPropValue(props.block.getDataKey("key"), props.block, getDataScriptValue, props.defaultProps);
			} else {
				value = getDataScriptValue(props.block.getDataKey("key"));
			}
			innerHTML = value ?? innerHTML;
		}
		props.block.dynamicValues
			?.filter((dataKeyObj: BlockDataKey) => {
				return dataKeyObj.property === "innerHTML" && dataKeyObj.type === "key";
			})
			?.forEach((dataKeyObj: BlockDataKey) => {
				let value;
				if (dataKeyObj.comesFrom === "props") {
					value = getPropValue(dataKeyObj.key as string, props.block, getDataScriptValue, props.defaultProps);
				} else {
					value = getDataScriptValue(dataKeyObj.key as string);
				}
				innerHTML = value ?? innerHTML;
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
