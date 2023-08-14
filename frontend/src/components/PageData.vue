<template>
	<div>
		<CodeEditor v-model="page.page_data" type="JSON"></CodeEditor>
	</div>
</template>
<script lang="ts" setup>
import useStore from "@/store";
import CodeEditor from "./CodeEditor.vue";
const store = useStore();

const page = store.getActivePage();
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
