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
			</div>
			<div class="h-full" v-if="mode == 'component'">
				<CodeEditor
					v-model="componentDataPreview"
					type="JSON"
					label="Component Data Preview"
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
			<div v-else-if="mode == 'block'" class="mt-2 text-center text-sm text-ink-gray-6">
				Select a block to edit script
			</div>
		</div>
		<div
			class="absolute bottom-0 left-0 box-border flex w-full items-center justify-between border-t bg-surface-white p-4 py-2">
			<h2 class="text-base text-ink-gray-6">Mode</h2>
			<TabButtons class="w-fit" :buttons="modeButtons" v-model="mode" />
		</div>
		<Dialog class="overscroll-none" :title="dialogTitle" size="7xl" :isDirty="isDirty" v-model="showDialog">
			<template #default>
				<div v-if="mode == 'page'">
					<div v-if="currentScriptEditor == 'client'">
						<ClientScriptManager
							parentDoctype="Builder Page"
							:parentName="pageStore.activePage?.name as string"
							ref="clientScriptManager"></ClientScriptManager>
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
				<div v-if="mode == 'component'">
					<div v-if="currentScriptEditor == 'client'">
						<ClientScriptManager
							parentDoctype="Builder Component"
							:parentName="currentComponentName"
							ref="componentClientScriptManager"></ClientScriptManager>
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
								class="-mt-5 w-1/3 [&>div>div]:bg-surface-white"
								height="calc(100% - 110px)"
								description='Use Component Data Script to provide dynamic data to your component.<br>
								<b>Example:</b> data.items = frappe.get_list("Item")<br><br>
								Props are accessible via the <b>props</b> object.'
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
import webComponent from "@/data/webComponent";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import useComponentStore from "@/stores/componentStore";
import { BuilderPage } from "@/types/doctypes";
import blockController from "@/utils/blockController";
import { useStorage } from "@vueuse/core";
import { toast } from "frappe-ui";
import { useTelemetry } from "frappe-ui/frappe";
import { computed, defineComponent, ref, watch } from "vue";
import CodeEditor from "./Controls/CodeEditor.vue";
import TabButtons from "./Controls/TabButtons.vue";
import ClientScriptManager from "./ClientScriptManager.vue";
import PropsEditor from "./PropsEditor.vue";
import useCanvasStore from "@/stores/canvasStore.js";

const { capture } = useTelemetry();

const pageStore = usePageStore();
const componentStore = useComponentStore();
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

const clientScriptManager = ref<null | InstanceType<typeof ClientScriptManager>>(null);
const componentClientScriptManager = ref<null | InstanceType<typeof ClientScriptManager>>(null);
const dataScriptEditor = ref<null | InstanceType<typeof CodeEditor>>(null);
const componentDataScriptEditor = ref<null | InstanceType<typeof CodeEditor>>(null);

const currentScriptEditor = ref<"client" | "data">("client");
const isBlockSelected = computed(() => {
	return blockController.getFirstSelectedBlock();
});

const isFragmentMode = computed(() => canvasStore.editingMode == "fragment");

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

const currentComponentName = computed(() => {
	if (isFragmentMode.value && canvasStore.fragmentData) {
		return canvasStore.fragmentData.fragmentId || "";
	}
	return "";
});

const componentDataPreview = computed(() => {
	const componentId = currentComponentName.value;
	if (!componentId) {
		return {};
	}
	return componentStore.getComponentInstanceData(componentId, canvasStore.fragmentData.block?.blockId);
});

const componentDataScript = computed(() => {
	const name = currentComponentName.value;
	if (!name) return "";
	const doc = componentStore.getComponent(name);
	console.log(doc, 99);
	return doc?.component_data_script || "";
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

const saveComponentDataScript = (value: string) => {
	const name = currentComponentName.value;
	if (!name) return;

	webComponent.setValue
		.submit({
			name: name,
			component_data_script: value,
		})
		.then(async () => {
			capture("builder_component_data_script_saved");
			const doc = componentStore.getComponent(name);
			if (doc) {
				doc.component_data_script = value;
			}
			// Pass default props when re-fetching so the preview reflects prop-dependent data
			const block = blockController.getComponentRootBlock(blockController.getFirstSelectedBlock());
			const blockProps = block.getBlockProps();
			const defaultProps: Record<string, any> = {};
			for (const [propName, config] of Object.entries(blockProps)) {
				console.log(propName, config, 99);
				if (config.isStandard && config.propOptions?.options?.defaultValue !== undefined) {
					defaultProps[propName] = config.propOptions.options.defaultValue;
				} else if (config.value) {
					defaultProps[propName] = config.value;
				}
			}
			console.log(defaultProps, 99);
			await componentStore.setComponentData(name, defaultProps);
			toast.success("Component data script saved");
		})
		.catch((e: { message: string; exc: string }) => {
			const errorMessage = e.exc?.split("\n").slice(-2)[0];
			toast.error("Failed to save script", {
				description: errorMessage,
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
	if (currentScriptEditor.value === "data") {
		if (mode.value === "component" && componentDataScriptEditor.value) {
			return componentDataScriptEditor.value.isDirty;
		}
		if (dataScriptEditor.value) {
			return dataScriptEditor.value.isDirty;
		}
	} else if (currentScriptEditor.value === "client") {
		if (mode.value === "component" && componentClientScriptManager.value?.scriptEditor) {
			return componentClientScriptManager.value?.scriptEditor.isDirty;
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
