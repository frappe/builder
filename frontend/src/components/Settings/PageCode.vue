<template>
	<div class="no-scrollbar flex flex-col gap-6 overflow-auto">
		<CodeEditor
			label="<head> HTML"
			type="HTML"
			:readonly="builderStore.readOnlyMode"
			description="Add meta tags, styles, and scripts to page head"
			height="200px"
			class="shrink-0"
			:modelValue="pageStore.activePage?.head_html"
			@update:modelValue="(val) => pageStore.updateActivePage('head_html', val)"
			:showLineNumbers="true"></CodeEditor>
		<CodeEditor
			label="<body> HTML"
			type="HTML"
			:readonly="builderStore.readOnlyMode"
			description="Add scripts to page body"
			:modelValue="pageStore.activePage?.body_html"
			height="200px"
			class="shrink-0"
			@update:modelValue="pageStore.updateActivePage('body_html', $event)"
			:showLineNumbers="true"></CodeEditor>
	</div>
</template>
<script setup lang="ts">
import CodeEditor from "@/components/Controls/CodeEditor.vue";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";

const builderStore = useBuilderStore();
const pageStore = usePageStore();

// const libraryURL = ref("");
// const builderStore = useBuilderStore();

// const addLibraryURL = () => {
// 	if (libraryURL.value) {
// 		pageStore.updateActivePage("libraries", [...pageStore.activePage.libraries, libraryURL.value]);
// 		libraryURL.value = "";
// 	}
// };

// const scripts = [
// 	{
// 		type: "js",
// 		script_url: "https://cdn.jsdelivr.net/npm/vue@3.2.20/dist/vue.global.prod.js",
// 	},
// 	{
// 		type: "css",
// 		script_url: "https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css",
// 	},
// ];
</script>
