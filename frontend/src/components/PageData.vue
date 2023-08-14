<template>
	<div>
		<InlineInput v-model="block.blockDataSource">DocType</InlineInput>
		<span class="my-5 inline-block w-full text-center text-sm text-gray-600">-- OR --</span>
		<InlineInput>Endpoint</InlineInput>
		<CodeEditor v-model="page.page_data" type="JSON"></CodeEditor>
	</div>
</template>
<script lang="ts" setup>
import useStore from "@/store";
import Block from "@/utils/block";
import CodeEditor from "./CodeEditor.vue";
import InlineInput from "./InlineInput.vue";
const store = useStore();

const page = store.getActivePage();

defineProps({
	block: {
		type: Block,
		required: true,
	},
});
</script>
<style scoped>
:deep(.ace_editor) {
	height: 200px;
	width: 100%;
	border-radius: 5px;
	overscroll-behavior: none;
}
:deep(.ace_scrollbar) {
	display: none;
}
</style>
