<template>
	<div ref="component">
		<div
			v-if="!block.hasChildren()"
			class="pointer-events-none flex h-full w-full items-center justify-center font-semibold">
			Add a block to repeat
		</div>
		<BuilderBlock
			v-else
			:data="repeatingFrom == 'dataScript' ? _data : {}"
			:defaultProps="repeatingFrom == 'props' ? _data : null"
			:block="block.children[0]"
			:preview="Number(index) !== 0 || preview"
			:readonly="readonly"
			:breakpoint="breakpoint"
			:isChildOfComponent="block.isExtendedFromComponent()"
			v-for="(_data, index) in blockData" />
	</div>
</template>

<script setup lang="ts">
import type Block from "@/block";
import usePageStore from "@/stores/pageStore";
import { getDataForKey, getStandardPropValue } from "@/utils/helpers";
import { Ref, computed, ref } from "vue";
import BuilderBlock from "./BuilderBlock.vue";
import blockController from "@/utils/blockController";

const pageStore = usePageStore();

const props = withDefaults(
	defineProps<{
		block: Block;
		preview?: boolean;
		breakpoint?: string;
		data?: Record<string, any> | null;
		readonly?: boolean;
	}>(),
	{
		preview: false,
		breakpoint: "desktop",
		readonly: false,
	},
);

const component = ref(null) as Ref<HTMLElement | null>;

const repeatingFrom = computed(() => {
	return props.block.getDataKey("comesFrom") || "dataScript";
});

const blockData = computed(() => {
	const pageData = props.data || pageStore.pageData;
	const key = props.block.getDataKey("key");
	if (pageData && repeatingFrom.value === "dataScript" && key) {
		const data = getDataForKey(pageData, key);
		if (Array.isArray(data)) {
			return data.slice(0, 100);
		}
		return data;
	} else if (repeatingFrom.value == "props" && key) {
		const defaultProps: BlockProps[] = [];
		const componentRoot = blockController.getComponentRootBlock(props.block);
		const parsedValue = getStandardPropValue(key, componentRoot)?.value;
		if (Array.isArray(parsedValue)) {
			parsedValue.slice(0, 100).forEach((item: any) =>
				defaultProps.push({
					item: {
						value: item,
						isStandard: false,
						type: "static",
					},
				}),
			);
		} else if (typeof parsedValue === "object" && parsedValue !== null) {
			Object.entries(parsedValue)
				.slice(0, 100)
				.forEach(([key, value]) => {
					defaultProps.push({
						key: {
							value: key,
							isStandard: false,
							type: "static",
						},
						value: {
							value: typeof value !== "string" ? JSON.stringify(value) : value,
							isStandard: false,
							type: "static",
						},
					});
				});
		}

		return defaultProps;
	} else {
		return [{}];
	}
});

defineExpose({
	component,
});
</script>
