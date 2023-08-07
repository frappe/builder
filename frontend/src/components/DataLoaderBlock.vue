<template>
	<div ref="component">
		<div v-if="!block.hasChildren()" class="flex h-52 w-52 items-center justify-center">Drop A Component</div>
		<BuilderBlock
			v-else
			:data="data"
			:block="block.children[0]"
			:preview="preview"
			:breakpoint="breakpoint"
			:isChildOfComponent="block.isComponent()"
			v-for="data in block.blockData" />
	</div>
</template>

<script setup lang="ts">
import Block from "@/utils/block";
import { Ref, ref } from "vue";
import BuilderBlock from "./BuilderBlock.vue";

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

defineExpose({
	component,
});
</script>
