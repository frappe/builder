<template>
	<div ref="component">
		<div
			v-if="!block.hasChildren()"
			class="pointer-events-none flex h-52 w-52 items-center justify-center font-semibold">
			Drop A Component
		</div>
		<BuilderBlock
			v-else
			:data="data"
			:block="block.children[0]"
			:preview="preview"
			:breakpoint="breakpoint"
			:isChildOfComponent="block.isComponent()"
			v-for="data in blockData" />
	</div>
</template>

<script setup lang="ts">
import useStore from "@/store";
import Block from "@/utils/block";
import { Ref, computed, ref } from "vue";
import BuilderBlock from "./BuilderBlock.vue";
const store = useStore();

const props = defineProps({
	block: {
		type: Block,
		required: true,
	},
	preview: {
		type: Boolean,
		default: false,
	},
	breakpoint: {
		type: String,
		default: "desktop",
	},
});

const component = ref(null) as Ref<HTMLElement | null>;

const blockData = computed(() => {
	const pageData = store.pageData;
	const data = {};
	Object.assign(data, props.block.blockData);
	if (pageData && props.block.dataKey?.key) {
		Object.assign(data, pageData[props.block.dataKey?.key]);
	}
	return data;
});

defineExpose({
	component,
});
</script>
