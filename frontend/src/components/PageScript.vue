<template>
	<div class="flex h-full flex-col justify-between">
		<div class="flex h-full flex-col gap-4 p-3">
			<div class="flex gap-2">
				<Button @click="showClientScriptEditor()" class="flex-1">Client Script</Button>
				<Button v-if="mode != 'blockTemplate'" @click="showServerScriptEditor()" class="flex-1">
					Data Script
				</Button>
			</div>

			<div class="h-full" v-if="mode == 'page'">
				<CodeEditor
					v-model="pageStore.pageData"
					type="JSON"
					label="Page Data Preview"
					:autofocus="false"
					:readonly="true" />
			</div>
			<div class="h-fit" v-if="mode == 'component'">
				<CodeEditor
					v-model="componentDataPreview"
					type="JSON"
					label="Component Data Preview"
					:autofocus="false"
					:readonly="true" />
			</div>
			<div
				class="box-border h-full overflow-y-auto pb-12"
				v-if="mode == 'component' || mode == 'blockTemplate'">
				<div class="flex min-h-full w-full flex-col gap-6">
					<div>
						<div class="mb-3 mt-4 text-sm text-ink-gray-8">
							{{ mode == "component" ? "Component Props" : "Block Props" }}
						</div>
						<PropsEditor :obj="fragmentProps" @update:obj="setFragmentProps" />
					</div>
				</div>
			</div>
		</div>
		<Dialog class="overscroll-none" :title="dialogTitle" size="7xl" :isDirty="isDirty" v-model="showDialog">
			<template #title>
				<div class="flex w-full items-center justify-between gap-3 pr-2">
					<span class="text-lg font-semibold text-ink-gray-9">{{ dialogTitle }}</span>
					<TabButtons
						v-if="showBlockClientScriptToggle"
						v-model="activeBlockClientScript"
						:buttons="blockClientScriptTabs"
						class="w-48" />
				</div>
			</template>
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
								class="-mt-5 w-1/3 [&>div>div]:bg-surface-base"
								height="calc(100% - 110px)"
								description='Use Data Script to provide dynamic data to your web page.<br>
								<b>Example:</b> data.events = frappe.get_list("Event")<br><br>
								For more details on how to write data script, refer to <b><a class="underline" href="https://docs.frappe.io/builder/data-script" target="_blank">this documentation</a></b>.
								'
								:readonly="true"></CodeEditor>
						</div>
					</div>
				</div>
				<div v-if="mode == 'component' || mode == 'blockTemplate'">
					<div v-if="currentScriptEditor == 'client'">
						<div class="flex h-full flex-col">
							<CodeEditor
								v-show="activeBlockClientScript === 'js'"
								ref="blockJavaScriptEditor"
								:modelValue="blockJavaScript"
								type="JavaScript"
								label="Block JavaScript"
								height="60vh"
								:readonly="builderStore.readOnlyMode"
								:autofocus="true"
								@save="(value: string) => saveBlockClientScript('js', value)"
								:showSaveButton="true"
								:show-line-numbers="true"></CodeEditor>
							<CodeEditor
								v-show="activeBlockClientScript === 'css'"
								ref="blockCSSEditor"
								:modelValue="blockCSS"
								type="CSS"
								label="Block CSS"
								height="60vh"
								:readonly="builderStore.readOnlyMode"
								:autofocus="false"
								@save="(value: string) => saveBlockClientScript('css', value)"
								:showSaveButton="true"
								:show-line-numbers="true"></CodeEditor>
						</div>
					</div>
					<div v-else-if="mode == 'component'">
						<div class="flex gap-4">
							<CodeEditor
								class="w-2/3 overscroll-none"
								ref="componentDataScriptEditor"
								v-model="componentDataScript"
								type="Python"
								mode="page"
								height="60vh"
								:readonly="builderStore.readOnlyMode"
								:autofocus="true"
								@save="saveComponentDataScript"
								:showSaveButton="true"
								:show-line-numbers="true"></CodeEditor>
							<CodeEditor
								v-model="componentDataPreview"
								type="JSON"
								label="Component Data Preview"
								:showLineNumbers="true"
								class="[&>div>div]:bg-surface-white -mt-5 w-1/3"
								height="calc(100% - 110px)"
								description='Use Component Data Script to provide dynamic data to your component.<br>
								<b>Example:</b> data.items = frappe.get_list("Item")<br><br>
								Props are accessible via the <b>props</b> object.'
								:readonly="true"></CodeEditor>
						</div>
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
import useCanvasStore from "@/stores/canvasStore.js";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/doctypes";
import componentController from "@/utils/componentController";
import { toast } from "frappe-ui";
import { useTelemetry } from "frappe-ui/frappe";
import { computed, defineComponent, ref, watch } from "vue";
import CodeEditor from "./Controls/CodeEditor.vue";
import TabButtons from "./Controls/TabButtons.vue";
import PageClientScriptManager from "./PageClientScriptManager.vue";
import PropsEditor from "./PropsEditor.vue";

const { capture } = useTelemetry();

const pageStore = usePageStore();
const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();

const { currentComponentId, componentDataPreview, componentDataScript } = componentController;

const showDialog = ref(false);
const activeBlockClientScript = ref<"js" | "css">("js");

const props = defineProps<{
	page: BuilderPage;
}>();

const clientScriptManager = ref<null | InstanceType<typeof PageClientScriptManager>>(null);
const dataScriptEditor = ref<null | InstanceType<typeof CodeEditor>>(null);
const componentDataScriptEditor = ref<null | InstanceType<typeof CodeEditor>>(null);
const blockJavaScriptEditor = ref<null | InstanceType<typeof CodeEditor>>(null);
const blockCSSEditor = ref<null | InstanceType<typeof CodeEditor>>(null);

const currentScriptEditor = ref<"client" | "data">("client");
const mode = computed<"page" | "component" | "blockTemplate">(() => {
	if (canvasStore.editingMode !== "fragment") return "page";
	return canvasStore.fragmentData.fragmentType || "component";
});

const blockClientScriptTabs = [
	{ label: "JavaScript", value: "js", icon: "lucide-braces" },
	{ label: "CSS", value: "css", icon: "lucide-paintbrush" },
];

const blockJavaScript = computed(() => canvasStore.fragmentData.block?.clientScript.js || "");
const blockCSS = computed(() => canvasStore.fragmentData.block?.clientScript.css || "");
const fragmentProps = computed(() => canvasStore.fragmentData.block?.props || {});

const dialogTitle = computed(() => {
	const modeLabel = mode.value === "blockTemplate" ? "Block Template" : capitalize(mode.value);
	return currentScriptEditor.value == "data" ? `${modeLabel} Data Script` : `${modeLabel} Client Script`;
});

const showBlockClientScriptToggle = computed(() => {
	return mode.value !== "page" && currentScriptEditor.value === "client";
});

const capitalize = (value: string) => value.charAt(0).toUpperCase() + value.slice(1);

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

const saveComponentDataScript = async (value: string) => {
	if (!currentComponentId.value) return;
	componentController.setComponentDataScript(value);
};

const setFragmentProps = (props: BlockProps) => {
	const rootBlock = canvasStore.fragmentData.block;
	if (!rootBlock) return;
	rootBlock.props = props;
	canvasStore.activeCanvas?.toggleDirty(true);
};

const saveBlockClientScript = (field: "js" | "css", value: string) => {
	const rootBlock = canvasStore.fragmentData.block;
	if (!rootBlock) return;
	rootBlock.clientScript[field] = value;
	canvasStore.activeCanvas?.toggleDirty(true);
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
	if (currentScriptEditor.value === "data") {
		if (mode.value === "component" && componentDataScriptEditor.value) {
			return componentDataScriptEditor.value.isDirty;
		}
		if (dataScriptEditor.value) {
			return dataScriptEditor.value.isDirty;
		}
	} else if (currentScriptEditor.value === "client") {
		if (mode.value !== "page") {
			return Boolean(blockJavaScriptEditor.value?.isDirty || blockCSSEditor.value?.isDirty);
		}
		if (clientScriptManager.value?.scriptEditor) {
			return clientScriptManager.value?.scriptEditor.isDirty;
		}
	}
	return false;
});

watch(
	() => builderStore.showDataScriptDialog,
	() => {
		if (builderStore.showDataScriptDialog !== null) {
			showServerScriptEditor();
			builderStore.showDataScriptDialog = null;
		}
	},
);
</script>
