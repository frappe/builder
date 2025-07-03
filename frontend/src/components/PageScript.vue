<template>
	<div class="flex flex-col gap-4">
		<div class="flex gap-2">
			<BuilderButton @click="showClientScriptEditor()" class="flex-1">Client Script</BuilderButton>
			<BuilderButton @click="showServerScriptEditor()" class="flex-1">Data Script</BuilderButton>
		</div>
		<CodeEditor v-model="pageStore.pageData" type="JSON" label="Data Preview" :readonly="true"></CodeEditor>
		<Dialog
			style="z-index: 40"
			class="overscroll-none"
			:options="{
				title: currentScriptEditor == 'data' ? 'Data Script' : 'Client Script',
				size: '7xl',
			}"
			:isDirty="isDirty"
			v-model="showDialog">
			<template #body-content>
				<div v-if="currentScriptEditor == 'client'">
					<PageClientScriptManager
						:page="pageStore.activePage as BuilderPage"
						ref="clientScriptManager"></PageClientScriptManager>
				</div>
				<div v-else>
					<div class="flex gap-4">
						<CodeEditor
							class="w-full overscroll-none"
							ref="dataScriptEditor"
							v-model="page.page_data_script"
							type="Python"
							height="60vh"
							:autofocus="true"
							@save="savePageDataScript"
							:showSaveButton="true"
							:show-line-numbers="true"></CodeEditor>
						<CodeEditor
							v-model="pageStore.pageData"
							type="JSON"
							label="Data Preview"
							class="-mt-5 w-1/3 [&>div>div]:bg-surface-white"
							height="calc(100% - 200px)"
							description='Use Data Script to provide dynamic data to your web page.<br>
								<b>Example:</b> data.events = frappe.get_list("Event")<br><br>
								For more details on how to write data script, refer to <b><a class="underline" href="https://docs.frappe.io/builder/data-script" target="_blank">this documentation</a></b>.
								'
							:readonly="true"></CodeEditor>
					</div>
				</div>
			</template>
		</Dialog>
	</div>
</template>
<script lang="ts" setup>
import Dialog from "@/components/Controls/Dialog.vue";
import { webPages } from "@/data/webPage";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { posthog } from "@/telemetry";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { computed, defineComponent, ref, watch } from "vue";
import { toast } from "vue-sonner";
import CodeEditor from "./Controls/CodeEditor.vue";
import PageClientScriptManager from "./PageClientScriptManager.vue";

const pageStore = usePageStore();
const builderStore = useBuilderStore();
const showDialog = ref(false);

const props = defineProps<{
	page: BuilderPage;
}>();

const clientScriptManager = ref<null | InstanceType<typeof PageClientScriptManager>>(null);
const dataScriptEditor = ref<null | InstanceType<typeof CodeEditor>>(null);

const currentScriptEditor = ref<"client" | "data">("client");

const savePageDataScript = (value: string) => {
	webPages.setValue
		.submit({
			name: props.page.name,
			page_data_script: value,
		})
		.then(() => {
			posthog.capture("builder_page_data_script_saved");
			props.page.page_data_script = value;
			pageStore.setPageData(props.page);
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

const isDirty = computed(() => {
	if (currentScriptEditor.value === "data" && dataScriptEditor.value) {
		return dataScriptEditor.value.isDirty;
	} else if (currentScriptEditor.value === "client" && clientScriptManager.value?.scriptEditor) {
		return clientScriptManager.value?.scriptEditor.isDirty;
	}
	return false;
});

watch(
	() => builderStore.showDataScriptDialog,
	() => {
		// if showDataScriptDialog is true, open the dialog
		if (builderStore.showDataScriptDialog) {
			showServerScriptEditor();
			builderStore.showDataScriptDialog = false; // reset the flag
		}
	},
);
</script>
