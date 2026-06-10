<template>
	<div class="flex h-full flex-col justify-between">
		<div class="flex h-full flex-col gap-4 p-3">
			<div class="flex gap-2" v-if="mode == 'page' || isBlockSelected">
				<Button @click="showClientScriptEditor()" class="flex-1">Client Script</Button>
				<Button v-if="mode == 'page'" @click="showServerScriptEditor()" class="flex-1">Data Script</Button>
			</div>

			<div class="h-full" v-if="mode == 'page'">
				<CodeEditor
					v-model="pageStore.pageData"
					type="JSON"
					label="Page Data Preview"
					:autofocus="false"
					:readonly="true" />
			</div>
			<div class="box-border h-full overflow-y-auto pb-12" v-if="mode == 'block' && showPropsInput">
				<div class="flex min-h-full w-full flex-col" v-if="isBlockSelected">
					<div class="my-3 mt-4 text-sm text-ink-gray-8">Block Props</div>
					<PropsEditor
						:obj="blockController.getBlockProps()"
						@update:obj="(obj: BlockProps) => blockController.setBlockProps(obj)" />
				</div>
			</div>
			<div v-else class="mt-2 text-center text-sm text-ink-gray-6">Select a block to edit script</div>
		</div>
		<div
			class="absolute bottom-0 left-0 box-border flex w-full items-center justify-between border-t bg-surface-white p-4 py-2">
			<h2 class="text-base text-ink-gray-6">Mode</h2>
			<TabButtons
				class="w-fit"
				:buttons="[
					{ label: 'Page', icon: 'lucide-layout', hideLabel: true, value: 'page', showTooltip: true },
					{ label: 'Block', icon: 'lucide-layers', hideLabel: true, value: 'block', showTooltip: true },
				]"
				v-model="mode" />
		</div>
		<Dialog
			class="overscroll-none"
			:title="
				currentScriptEditor == 'data'
					? `${mode.charAt(0).toUpperCase() + mode.slice(1)} Data Script`
					: `${mode.charAt(0).toUpperCase() + mode.slice(1)} Client Script`
			"
			size="7xl"
			:isDirty="isDirty"
			v-model="showDialog">
			<template #default>
				<div v-if="mode == 'page'">
					<div v-if="currentScriptEditor == 'client'">
						<PageClientScriptManager
							:page="pageStore.activePage as BuilderPage"
							ref="clientScriptManager"></PageClientScriptManager>
					</div>
					<div v-else>
						<div class="flex gap-4">
							<CodeEditor
								class="w-2/3 overscroll-none"
								ref="dataScriptEditor"
								v-model="page.page_data_script"
								type="Python"
								mode="page"
								height="60vh"
								:readonly="builderStore.readOnlyMode"
								:autofocus="true"
								@save="savePageDataScript"
								:showSaveButton="true"
								:show-line-numbers="true"></CodeEditor>
							<CodeEditor
								v-model="pageStore.pageData"
								type="JSON"
								label="Data Preview"
								:showLineNumbers="true"
								class="-mt-5 w-1/3 [&>div>div]:bg-surface-white"
								height="calc(100% - 110px)"
								description='Use Data Script to provide dynamic data to your web page.<br>
								<b>Example:</b> data.events = frappe.get_list("Event")<br><br>
								For more details on how to write data script, refer to <b><a class="underline" href="https://docs.frappe.io/builder/data-script" target="_blank">this documentation</a></b>.
								'
								:readonly="true"></CodeEditor>
						</div>
					</div>
				</div>
				<div v-if="mode == 'block'">
					<CodeEditor
						class="overscroll-none"
						ref="blockClientScriptEditor"
						v-model="blockClientScript"
						type="JavaScript"
						mode="block"
						height="60vh"
						:readonly="builderStore.readOnlyMode"
						:autofocus="true"
						@save="saveBlockClientScript"
						:showSaveButton="true"
						:show-line-numbers="true"
						description='Use Block Client Script to add interactivity to your block. You can access the current DOM node using the keyword `this`. All Block props are accessible using the read-only `props` object.<br>
						<b>Example:</b> <pre style="display:inline; font-size: 11px;">this.addEventListener("click", () => { console.log(props) })</pre><br><br>
						For more details on how to write data script, refer to <b><a class="underline" href="https://docs.frappe.io/builder/data-script" target="_blank">this documentation</a></b>.'></CodeEditor>
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
import { BuilderPage } from "@/types/doctypes";
import blockController from "@/utils/blockController";
import { useStorage } from "@vueuse/core";
import { toast } from "frappe-ui";
import { useTelemetry } from "frappe-ui/frappe";
import { computed, defineComponent, ref, watch } from "vue";
import CodeEditor from "./Controls/CodeEditor.vue";
import TabButtons from "./Controls/TabButtons.vue";
import PageClientScriptManager from "./PageClientScriptManager.vue";
import PropsEditor from "./PropsEditor.vue";
import useCanvasStore from "@/stores/canvasStore.js";

const { capture } = useTelemetry();

const pageStore = usePageStore();
const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();

const showPropsInput = computed(() => {
	return canvasStore.editingMode == "fragment" && !blockController.getFirstSelectedBlock()?.getParentBlock();
});

const showDialog = ref(false);
const mode = useStorage("builder_last_used_script_editor_mode", "page");

const props = defineProps<{
	page: BuilderPage;
}>();

const clientScriptManager = ref<null | InstanceType<typeof PageClientScriptManager>>(null);
const dataScriptEditor = ref<null | InstanceType<typeof CodeEditor>>(null);

const currentScriptEditor = ref<"client" | "data">("client");
const isBlockSelected = computed(() => {
	return blockController.getFirstSelectedBlock();
});

const blockClientScript = computed(() => {
	if (isBlockSelected.value) {
		return blockController.getFirstSelectedBlock()?.getBlockClientScript() || "";
	}
	return "";
});

const savePageDataScript = (value: string) => {
	webPages.setValue
		.submit({
			name: props.page.name,
			page_data_script: value,
		})
		.then(() => {
			capture("builder_page_data_script_saved");
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

const saveBlockClientScript = (value: string) => {
	if (isBlockSelected.value) {
		blockController.getFirstSelectedBlock()?.setBlockClientScript(value);
	}
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
		if (builderStore.showDataScriptDialog !== null) {
			mode.value = builderStore.showDataScriptDialog;
			showServerScriptEditor();
			builderStore.showDataScriptDialog = null; // reset the flag
		}
	},
);
</script>
