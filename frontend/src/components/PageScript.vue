<template>
	<div class="absolute bottom-0 z-50 h-fit w-full bg-white dark:bg-gray-900">
		<CodeEditor
			v-model="page.client_script"
			type="JavaScript"
			height="400px"
			:show-line-numbers="true"></CodeEditor>
	</div>
</template>
<script setup lang="ts">
import { webPages } from "@/data/webPage";
import useStore from "@/store";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { watchDebounced } from "@vueuse/core";
import { ref } from "vue";
import CodeEditor from "./CodeEditor.vue";

const store = useStore();
const page = ref<BuilderPage>(store.getActivePage());

watchDebounced(
	() => page.value.client_script,
	() => {
		if (!page.value) return;
		webPages.setValue
			.submit({
				name: page.value.name,
				client_script: page.value.client_script,
			})
			.then(() => {
				close();
				store.setPageData();
			});
	},
	{ deep: true }
);
</script>
