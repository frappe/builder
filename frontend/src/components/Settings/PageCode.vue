<template>
	<div class="no-scrollbar flex flex-col gap-6 overflow-auto">
		<!-- <div>
			<div class="">
				<InputLabel>Add Library</InputLabel>
				<div class="mb-2 flex">
					<BuilderInput class="w-full" v-model="libraryURL"></BuilderInput>
					<BuilderButton class="ml-2" :disabled="!libraryURL" @click="addLibraryURL">Add</BuilderButton>
				</div>
			</div>
			<div class="flex flex-col gap-2">
				<div v-for="script in scripts" class="rounded bg-surface-gray-2 px-3 pr-0 shadow-sm">
					<div class="flex w-full items-center justify-between gap-2">
						<div class="flex items-center gap-2">
							<span class="text-ink-gray-4">{{ script.type }}</span>
							<a href="{{ script.script_url }}" class="text-sm hover:underline">{{ script.script_url }}</a>
						</div>
						<BuilderButton class="ml-2 text-sm">Remove</BuilderButton>
					</div>
				</div>
			</div>
		</div> -->
		<CodeEditor
			label="<head> HTML"
			type="HTML"
			description="Add meta tags, styles, and scripts to page head"
			height="200px"
			class="shrink-0"
			:modelValue="pageStore.activePage?.head_html"
			@update:modelValue="(val) => pageStore.updateActivePage('head_html', val)"
			:showLineNumbers="true"></CodeEditor>
		<CodeEditor
			label="<body> HTML"
			type="HTML"
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
import usePageStore from "@/stores/pageStore";
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
