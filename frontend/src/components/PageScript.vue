<template>
	<div class="flex flex-col gap-4">
		<div class="flex gap-2">
			<Button
				@click="showClientScriptEditor()"
				class="flex-1 text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700">
				Client Script
			</Button>
			<Button
				@click="showServerScriptEditor()"
				class="flex-1 text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700">
				Data Script
			</Button>
		</div>
		<CodeEditor v-model="store.pageData" type="JSON" label="Data Preview" :readonly="true"></CodeEditor>
		<Dialog
			style="z-index: 40"
			class="overscroll-none"
			:options="{
				title: currentScriptEditor == 'data' ? 'Data Script' : 'Client Script',
				size: '7xl',
			}"
			v-model="showDialog">
			<template #body-content>
				<div v-if="currentScriptEditor == 'client'">
					<PageClientScriptManager :page="store.activePage as BuilderPage"></PageClientScriptManager>
				</div>
				<div v-else>
					<CodeEditor
						class="overscroll-none"
						v-model="page.page_data_script"
						type="Python"
						height="60vh"
						:show-line-numbers="true"></CodeEditor>
					<span class="text-xs text-gray-600 dark:text-zinc-400">
						Can be used to fetch dynamic data from server and pass it to the page.
						<br />
						eg. data.events = frappe.get_list("Event")
					</span>
					<div class="mt-2 flex flex-1">
						<Button
							@click="savePageDataScript"
							class="w-full text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700">
							Save
						</Button>
					</div>
				</div>
			</template>
		</Dialog>
	</div>
</template>
<script lang="ts" setup>
import { webPages } from "@/data/webPage";
import useStore from "@/store";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { Dialog } from "frappe-ui";
import posthog from "posthog-js";
import { ref } from "vue";
import CodeEditor from "./CodeEditor.vue";
import PageClientScriptManager from "./PageClientScriptManager.vue";
const store = useStore();
const showDialog = ref(false);

const props = defineProps<{
	page: BuilderPage;
}>();

const currentScriptEditor = ref<"client" | "data">("client");

const savePageDataScript = () => {
	webPages.setValue
		.submit({
			name: props.page.name,
			page_data_script: props.page.page_data_script,
		})
		.then(() => {
			posthog.capture("builder_page_data_script_saved");
			showDialog.value = false;
			store.setPageData(props.page);
		});
};

const showClientScriptEditor = () => {
	currentScriptEditor.value = "client";
	showDialog.value = true;
};

const showServerScriptEditor = () => {
	currentScriptEditor.value = "data";
	showDialog.value = true;
};
</script>
<style></style>
