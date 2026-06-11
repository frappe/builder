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
import { getDataForKey, getPropValue } from "@/utils/helpers";
import { computed, ref } from "vue";

const component = ref<HTMLElement | null>(null);
const props = defineProps<{
	block: Block;
	data?: Record<string, unknown> | null;
	componentData?: Record<string, unknown> | null;
	defaultProps?: BlockProps | null;
}>();

const hasBlockProps = computed(() => {
	return props.defaultProps || Object.keys(props.block.getBlockProps()).length > 0;
});

const hasComponentData = computed(() => {
	return props.componentData && Object.keys(props.componentData).length > 0;
});

const getDataScriptValue = (path: string): any => {
	return getDataForKey(props.data || {}, path);
};

const getComponentDataValue = (path: string): any => {
	return getDataForKey(props.componentData || {}, path);
};

const getDynamicContent = () => {
	let innerHTML = null as string | null;
	if (props.data || hasBlockProps.value || hasComponentData.value) {
		if (props.block.getDataKey("property") === "innerHTML") {
			let value;
			if (props.block.getDataKey("comesFrom") === "props") {
				value = getPropValue(
					props.block.getDataKey("key"),
					props.block,
					getDataScriptValue,
					props.defaultProps,
					getComponentDataValue,
				);
			} else {
				value = getDataScriptValue(props.block.getDataKey("key"));
			}
			innerHTML = value ?? innerHTML;
		}
		props.block
			.getDynamicValues()
			?.filter((dataKeyObj: BlockDataKey) => {
				return dataKeyObj.property === "innerHTML" && dataKeyObj.type === "key";
			})
			?.forEach((dataKeyObj: BlockDataKey) => {
				let value;
				if (dataKeyObj.comesFrom === "props") {
					value = getPropValue(
						dataKeyObj.key as string,
						props.block,
						getDataScriptValue,
						props.defaultProps,
						getComponentDataValue,
					);
				} else if (dataKeyObj.comesFrom === "componentData") {
					value = getComponentDataValue(dataKeyObj.key as string);
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
	if (props.data || hasBlockProps.value || hasComponentData.value) {
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
