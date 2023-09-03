<template>
	<div>
		<Button @click="showDialog = !showDialog" class="text-base" icon-left="code">Set Data Script</Button>
		<CodeEditor
			v-model="store.pageData"
			type="JSON"
			label="Page Data Preview"
			:readonly="true"
			class="mt-8"></CodeEditor>
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
				<span class="text-xs text-gray-600">
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
import { WebPageBeta } from "@/types/WebsiteBuilder/WebPageBeta";
import { Dialog } from "frappe-ui";
import { onMounted, ref } from "vue";
import CodeEditor from "./CodeEditor.vue";
const store = useStore();
const showDialog = ref(false);
const page = ref<WebPageBeta>(store.getActivePage());

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
