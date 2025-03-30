<template>
	<div ref="component">
		<div
			v-if="!block.hasChildren()"
			class="pointer-events-none flex h-full w-full items-center justify-center font-semibold">
			Add a block to repeat
		</div>
		<BuilderBlock
			v-else
			:data="_data"
			:block="block.children[0]"
			:preview="index !== 0 || preview"
			:breakpoint="breakpoint"
			:isChildOfComponent="block.isExtendedFromComponent()"
			v-for="(_data, index) in blockData" />
	</div>
</template>

<script setup lang="ts">
import type Block from "@/block";
import usePageStore from "@/stores/pageStore";
import { getDataForKey } from "@/utils/helpers";
import { Ref, computed, ref } from "vue";
import BuilderBlock from "./BuilderBlock.vue";

const pageStore = usePageStore();

const props = withDefaults(
	defineProps<{
		block: Block;
		preview?: boolean;
		breakpoint?: string;
		data?: Record<string, any> | null;
	}>(),
	{
		preview: false,
		breakpoint: "desktop",
	},
);

const component = ref(null) as Ref<HTMLElement | null>;

const blockData = computed(() => {
	const pageData = props.data || pageStore.pageData;
	if (pageData && props.block.getDataKey("key")) {
		const data = getDataForKey(pageData, props.block.getDataKey("key"));
		if (Array.isArray(data)) {
			return data.slice(0, 100);
		}
		return data;
	} else {
		return [{}];
	}
});

defineExpose({
	component,
});
</script>
