<template>
	<div ref="component">
		<div
			v-if="!block.hasChildren()"
			class="pointer-events-none flex h-full w-full items-center justify-center font-semibold">
			Add a block to repeat
		</div>
		<BuilderBlock
			v-else
			:data="repeatingFrom == 'dataScript' ? _data : data"
			:componentData="repeatingFrom == 'componentData' ? _data : componentData"
			:defaultProps="repeatingFrom == 'props' ? _data : null"
			:block="block.children[0]"
			:preview="Number(index) !== 0 || preview"
			:readonly="readonly"
			:breakpoint="breakpoint"
			:isChildOfComponent="block.isExtendedFromComponent()"
			:repeater-index="getRepeaterIndex(index)"
			v-for="(_data, index) in blockRepeaterData" />
	</div>
</template>

<script setup lang="ts">
import type Block from "@/block";
import usePageStore from "@/stores/pageStore";
import { getDataForKey, getStandardPropValue } from "@/utils/helpers";
import { Ref, computed, ref } from "vue";
import BuilderBlock from "./BuilderBlock.vue";

const pageStore = usePageStore();

const props = withDefaults(
	defineProps<{
		block: Block;
		repeaterIndex?: string | number | null;
		preview?: boolean;
		breakpoint?: string;
		data?: Record<string, any> | null;
		componentData?: Record<string, any> | null;
		readonly?: boolean;
	}>(),
	{
		preview: false,
		breakpoint: "desktop",
		readonly: false,
		data: null,
		componentData: null,
	},
);

const component = ref(null) as Ref<HTMLElement | null>;

const repeatingFrom = computed(() => {
	return props.block.getDataKey("comesFrom") || "dataScript";
});

const blockRepeaterData = computed(() => {
	const pageData = props.data || pageStore.pageData;
	const key = props.block.getDataKey("key");
	if (pageData && repeatingFrom.value === "dataScript" && key) {
		const data = getDataForKey(pageData, key);
		if (Array.isArray(data)) {
			return data.slice(0, 100);
		}
		return data;
	} else if (repeatingFrom.value === "componentData" && key) {
		const compData = getDataForKey(props.componentData || {}, key);
		if (Array.isArray(compData)) {
			return compData.slice(0, 100);
		}
		return compData || [];
	} else if (repeatingFrom.value == "props" && key) {
		const defaultProps: BlockProps[] = [];
		const componentRoot = props.block.getComponentRoot();
		const parsedValue = getStandardPropValue(key, componentRoot)?.value;
		if (Array.isArray(parsedValue)) {
			parsedValue.slice(0, 100).forEach((item: any) =>
				defaultProps.push({
					item: {
						value: item,
						isStandard: false,
						isDynamic: true,
						comesFrom: "props",
						isPassedDown: true,
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
							isDynamic: true,
							comesFrom: "props",
							isPassedDown: true,
						},
						value: {
							value: typeof value !== "string" ? JSON.stringify(value) : value,
							isStandard: false,
							isDynamic: true,
							comesFrom: "props",
							isPassedDown: true,
						},
					});
				});
		}

		return defaultProps;
	} else {
		return [{}];
	}
});

const getRepeaterIndex = (index: number | string) => {
	if (props.repeaterIndex !== undefined) {
		const parsedPropIndex =
			typeof props.repeaterIndex === "string" ? parseInt(props.repeaterIndex, 10) : props.repeaterIndex;
		const parsedIndex = typeof index === "string" ? parseInt(index, 10) : index;
		return (parsedPropIndex || 0) * 10 + parsedIndex;
	}
	return index;
};

defineExpose({
	component,
});
</script>
