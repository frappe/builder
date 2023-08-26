<template>
	<div ref="component">
		<div
			v-if="!block.hasChildren()"
			class="pointer-events-none flex h-52 w-52 items-center justify-center font-semibold">
			Drop A Component
		</div>
		<BuilderBlock
			v-else
			:data="_data"
			:block="block.children[0]"
			:preview="index !== 0 || preview"
			:breakpoint="breakpoint"
			:isChildOfComponent="block.isComponent()"
			v-for="(_data, index) in blockData" />
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
	data: {
		type: Object,
		default: null,
	},
});

const component = ref(null) as Ref<HTMLElement | null>;

const blockData = computed(() => {
	const pageData = props.data || store.pageData;
	if (pageData && props.block.getDataKey("key")) {
		return pageData[props.block.getDataKey("key")];
	} else {
		return [{}];
	}
});

defineExpose({
	component,
});
</script>
