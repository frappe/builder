<template>
	<div class="flex flex-col gap-4">
		<div class="flex gap-2">
			<BuilderButton
				@click="showClientScriptEditor()"
				class="flex-1 bg-surface-gray-2 text-base text-text-icons-gray-8 hover:bg-surface-gray-3">
				Client Script
			</BuilderButton>
			<BuilderButton
				@click="showServerScriptEditor()"
				class="flex-1 bg-surface-gray-2 text-base text-text-icons-gray-8 hover:bg-surface-gray-3">
				Data Script
			</BuilderButton>
		</div>
		<CodeEditor v-model="store.pageData" type="JSON" label="Data Preview" :readonly="true"></CodeEditor>
		<Dialog
			style="z-index: 40"
			class="overscroll-none"
			:disableOutsideClickToClose="true"
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
						height="65vh"
						@save="savePageDataScript"
						:showSaveButton="true"
						description='Use Data Script to provide dynamic data to your web page.<br>
						<b>Example:</b> data.events = frappe.get_list("Event")<br><br>
						For more details on how to write data script, refer to <b><a class="underline" href="https://docs.frappe.io/builder/data-script" target="_blank">this documentation</a></b>.
						'
						:show-line-numbers="true"></CodeEditor>
				</div>
			</template>
		</Dialog>
	</div>
</template>
<script lang="ts" setup>
import { webPages } from "@/data/webPage";
import useStore from "@/store";
import { posthog } from "@/telemetry";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { Dialog } from "frappe-ui";
import { defineComponent, ref } from "vue";
import { toast } from "vue-sonner";
import CodeEditor from "./Controls/CodeEditor.vue";
import PageClientScriptManager from "./PageClientScriptManager.vue";
const store = useStore();
const showDialog = ref(false);

const props = defineProps<{
	page: BuilderPage;
}>();

const currentScriptEditor = ref<"client" | "data">("client");

const savePageDataScript = (value: string) => {
	webPages.setValue
		.submit({
			name: props.page.name,
			page_data_script: value,
		})
		.then(() => {
			posthog.capture("builder_page_data_script_saved");
			showDialog.value = false;
			props.page.page_data_script = value;
			store.setPageData(props.page);
			toast.success("Data script saved");
		})
		.catch((e: { message: string; exc: string; messages: [string] }) => {
			let errorMessage = e.exc?.split("\n").slice(-2)[0];
			if (!errorMessage) {
				errorMessage = e.messages[0];
			}
			toast.error("Failed to save script", {
				description: defineComponent({
					template: `<div>${errorMessage}</div>`,
				}),
			});
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
