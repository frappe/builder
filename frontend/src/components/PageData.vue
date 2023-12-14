<template>
	<div>
		<Button
			@click="showDialog = !showDialog"
			class="text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
			icon-left="code">
			Set Data Script
		</Button>
		<CodeEditor
			v-model="store.pageData"
			type="JSON"
			label="Page Data Preview"
			:readonly="true"
			class="mt-5"></CodeEditor>
		<Dialog
			style="z-index: 40"
			:options="{
				title: 'Page Data Script',
				size: '4xl',
				actions: [
					{
						label: 'Save',
						variant: 'solid',
						onClick: savePageDataScript,
					},
				],
			}"
			v-model="showDialog">
			<template #body-content>
				<CodeEditor
					v-model="page.page_data_script"
					type="Python"
					height="60vh"
					:show-line-numbers="true"></CodeEditor>
				<span class="text-xs text-gray-600 dark:text-zinc-400">
					data.events = frappe.get_list("Event")
					<br />
					<b>Note:</b>
					Each key value of data should be a list.
				</span>
			</template>
		</Dialog>
	</div>
</template>
<script lang="ts" setup>
import { webPages } from "@/data/webPage";
import useStore from "@/store";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { Dialog } from "frappe-ui";
import { onMounted, ref } from "vue";
import CodeEditor from "./CodeEditor.vue";
const store = useStore();
const showDialog = ref(false);
const page = ref<BuilderPage>(store.getActivePage());

onMounted(() => {
	page.value = store.getActivePage();
});

const savePageDataScript = ({ close }: { close: () => void }) => {
	webPages.setValue
		.submit({
			name: page.value.name,
			page_data_script: page.value.page_data_script,
		})
		.then(() => {
			close();
			store.setPageData();
		});
};
</script>
<style>
[id^="headlessui-dialog-panel"] {
	@apply dark:bg-zinc-800;
}
[id^="headlessui-dialog-panel"] > div {
	@apply dark:bg-zinc-800;
	@apply dark:text-zinc-50;
}

[id^="headlessui-dialog-panel"] header h3 {
	@apply dark:text-white;
}

[id^="headlessui-dialog-panel"] button svg path {
	@apply dark:fill-white;
}
[id^="headlessui-dialog-panel"] button {
	@apply dark:text-white;
	@apply dark:hover:bg-zinc-700;
	@apply dark:bg-zinc-900;
}
[id^="headlessui-dialog-panel"] input {
	@apply dark:bg-zinc-900;
	@apply dark:border-zinc-800;
}

[id^="headlessui-dialog-panel"] input:focus {
	@apply dark:ring-0;
	@apply dark:border-zinc-700;
}

[id^="headlessui-dialog-panel"] input[type="checkbox"]:checked {
	@apply dark:bg-zinc-700;
}

[id^="headlessui-dialog-panel"] input[type="checkbox"]:focus {
	@apply dark:ring-zinc-700;
	@apply dark:ring-offset-0;
}

[id^="headlessui-dialog-panel"] input[type="checkbox"]:hover {
	@apply dark:bg-zinc-900;
}

[id^="headlessui-dialog-panel"] label > span {
	@apply dark:text-gray-50;
}
</style>
