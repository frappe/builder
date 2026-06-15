<template>
	<div class="flex h-full flex-col justify-between">
		<div class="flex h-full flex-col gap-4 p-3">
			<div
				class="flex gap-2"
				v-if="mode == 'page' || mode == 'component' || (mode == 'block' && isBlockSelected)">
				<Button @click="showClientScriptEditor()" class="flex-1">Client Script</Button>
				<Button v-if="mode != 'block'" @click="showServerScriptEditor()" class="flex-1">Data Script</Button>
			</div>

			<div class="h-full" v-if="mode == 'page'">
				<CodeEditor
					v-model="pageStore.pageData"
					type="JSON"
					label="Page Data Preview"
					:autofocus="false"
					:readonly="true" />
				<div class="my-6">
					<div class="mb-3 text-sm text-ink-gray-8">Page Variables</div>
					<VarsEditor :obj="pageVars" @update:obj="savePageVars" />
				</div>
			</div>
			<div class="h-fit" v-if="mode == 'component'">
				<CodeEditor
					v-model="componentDataPreview"
					type="JSON"
					label="Component Data Preview"
					:autofocus="false"
					:readonly="true" />
			</div>
			<div class="box-border h-full overflow-y-auto pb-12" v-if="mode == 'component'">
				<div class="flex min-h-full w-full flex-col gap-6" v-if="isBlockSelected">
					<div>
						<div class="mb-3 mt-4 text-sm text-ink-gray-8">Component Props</div>
						<PropsEditor
							:obj="componentProps"
							@update:obj="(obj: BlockProps) => componentController.setComponentProps(obj)" />
					</div>
					<div>
						<div class="mb-3 text-sm text-ink-gray-8">Component Variables</div>
						<VarsEditor
							:obj="componentVars"
							@update:obj="(obj: BlockVars) => componentController.setComponentVars(obj)" />
					</div>
				</div>
			</div>
			<div v-else-if="mode == 'block'" class="mt-2 text-center text-sm text-ink-gray-6">
				Select a block to edit script
			</div>
		</div>
		<div
			v-if="false"
			class="bg-surface-white absolute bottom-0 left-0 box-border flex w-full items-center justify-between border-t p-4 py-2">
			<h2 class="text-base text-ink-gray-6">Mode</h2>
			<TabButtons class="w-fit" :buttons="modeButtons" v-model="mode" />
		</div>
		<Dialog class="overscroll-none" :title="dialogTitle" size="7xl" :isDirty="isDirty" v-model="showDialog">
			<template #title>
				<div class="flex w-full items-center justify-between gap-3 pr-2">
					<span class="text-xl font-semibold text-ink-gray-9">{{ dialogTitle }}</span>
					<TabButtons
						v-if="showComponentClientScriptToggle"
						v-model="activeComponentClientScript"
						:buttons="componentClientScriptTabs"
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
				<div v-if="mode == 'component'">
					<div v-if="currentScriptEditor == 'client'">
						<div class="flex h-full flex-col">
							<CodeEditor
								v-show="activeComponentClientScript === 'component_js'"
								ref="componentJavaScriptEditor"
								:modelValue="componentJavaScript"
								type="JavaScript"
								label="Component JavaScript"
								mode="component"
								height="60vh"
								:readonly="builderStore.readOnlyMode"
								:autofocus="true"
								@save="(value: string) => saveComponentClientScript('component_js', value)"
								:showSaveButton="true"
								:show-line-numbers="true"></CodeEditor>
							<CodeEditor
								v-show="activeComponentClientScript === 'component_css'"
								ref="componentCSSEditor"
								:modelValue="componentCSS"
								type="CSS"
								label="Component CSS"
								height="60vh"
								:readonly="builderStore.readOnlyMode"
								:autofocus="false"
								@save="(value: string) => saveComponentClientScript('component_css', value)"
								:showSaveButton="true"
								:show-line-numbers="true"></CodeEditor>
						</div>
					</div>
					<div v-else>
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
								Props are accessible via the <b>props</b> object. Component Variables are accessible via the <b>vars</b> object.'
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
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/doctypes";
import blockController from "@/utils/blockController";
import componentController from "@/utils/componentController";
import { useStorage } from "@vueuse/core";
import { toast } from "frappe-ui";
import { useTelemetry } from "frappe-ui/frappe";
import { computed, defineComponent, nextTick, ref, watch } from "vue";
import CodeEditor from "./Controls/CodeEditor.vue";
import TabButtons from "./Controls/TabButtons.vue";
import PropsEditor from "./PropsEditor.vue";
import VarsEditor from "./VarsEditor.vue";
import useCanvasStore from "@/stores/canvasStore.js";
import PageClientScriptManager from "./PageClientScriptManager.vue";

const { capture } = useTelemetry();

const pageStore = usePageStore();
const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();

const {
	currentComponentId,
	componentDataPreview,
	componentProps,
	componentVars,
	componentDataScript,
	componentJavaScript,
	componentCSS,
} = componentController;

const showDialog = ref(false);
const mode = useStorage("builder_last_used_script_editor_mode", "page");
const activeComponentClientScript = ref<"component_js" | "component_css">("component_js");

const props = defineProps<{
	page: BuilderPage;
}>();

const clientScriptManager = ref<null | InstanceType<typeof PageClientScriptManager>>(null);
const dataScriptEditor = ref<null | InstanceType<typeof CodeEditor>>(null);
const componentDataScriptEditor = ref<null | InstanceType<typeof CodeEditor>>(null);
const componentJavaScriptEditor = ref<null | InstanceType<typeof CodeEditor>>(null);
const componentCSSEditor = ref<null | InstanceType<typeof CodeEditor>>(null);

const currentScriptEditor = ref<"client" | "data">("client");
const isBlockSelected = computed(() => {
	return blockController.getFirstSelectedBlock();
});

const isFragmentMode = computed(() => canvasStore.editingMode == "fragment");

// TODO: Remove Block mode
const modeButtons = computed(() => {
	if (isFragmentMode.value) {
		return [
			{
				label: "Component",
				icon: "lucide-component",
				hideLabel: true,
				value: "component",
				showTooltip: true,
			},
			{ label: "Block", icon: "lucide-layers", hideLabel: true, value: "block", showTooltip: true },
		];
	}
	return [
		{ label: "Page", icon: "lucide-layout", hideLabel: true, value: "page", showTooltip: true },
		{ label: "Block", icon: "lucide-layers", hideLabel: true, value: "block", showTooltip: true },
	];
});

const componentClientScriptTabs = [
	{ label: "JavaScript", value: "component_js", icon: "lucide-braces" },
	{ label: "CSS", value: "component_css", icon: "lucide-paintbrush" },
];

watch(
	isFragmentMode,
	() => {
		if (isFragmentMode.value) {
			mode.value = "component";
		} else {
			mode.value = "page";
		}
	},
	{ immediate: true },
);

const dialogTitle = computed(() => {
	const modeLabel = mode.value.charAt(0).toUpperCase() + mode.value.slice(1);
	return currentScriptEditor.value == "data" ? `${modeLabel} Data Script` : `${modeLabel} Client Script`;
});

const showComponentClientScriptToggle = computed(() => {
	return mode.value === "component" && currentScriptEditor.value === "client";
});

const pageVars = computed(() => {
	return JSON.parse(props.page.page_vars ?? "{}");
});

const savePageVars = (vars: BlockVars) => {
	pageStore.updateActivePage("page_vars", JSON.stringify(vars));
	props.page.page_vars = JSON.stringify(vars);
};

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

const saveComponentClientScript = (field: "component_js" | "component_css", value: string) => {
	if (!currentComponentId.value) return;
	componentController.setComponentClientScript(value, field === "component_js" ? "js" : "css");
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
		if (mode.value === "component") {
			return Boolean(componentJavaScriptEditor.value?.isDirty || componentCSSEditor.value?.isDirty);
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
			mode.value = builderStore.showDataScriptDialog;
			showServerScriptEditor();
			builderStore.showDataScriptDialog = null;
		}
	},
);
</script>
