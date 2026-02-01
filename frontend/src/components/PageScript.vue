<template>
	<div class="flex h-full flex-col justify-between">
		<div class="flex h-full flex-col gap-4 p-4">
			<div class="flex gap-2" v-if="mode == 'page' || isBlockSelected">
				<BuilderButton @click="showClientScriptEditor()" class="flex-1">Client Script</BuilderButton>
				<BuilderButton @click="showServerScriptEditor()" class="flex-1">Data Script</BuilderButton>
			</div>

			<div class="h-full" v-if="mode == 'page'">
				<CodeEditor
					v-model="pageStore.pageData"
					type="JSON"
					label="Page Data Preview"
					:autofocus="false"
					:readonly="true" />
			</div>
			<div class="box-border h-full overflow-y-auto pb-12" v-if="mode == 'block'">
				<div class="flex min-h-full w-full flex-col" v-if="isBlockSelected">
					<CodeEditor
						v-model="blockData"
						class="max-h-[70%]"
						type="JSON"
						label="Block Data Preview"
						:autofocus="false"
						:readonly="true"></CodeEditor>
					<div class="flex w-full items-center justify-between py-4">
						<div class="text-sm text-ink-gray-6">Show cumulative data</div>
						<Switch
							:model-value="showCumulativeBlockData"
							@update:model-value="(val) => (showCumulativeBlockData = val)" />
					</div>
					<div class="my-3 mt-4 text-sm text-ink-gray-8">Block Props</div>
					<PropsEditor
						:obj="blockController.getBlockProps()"
						@update:obj="(obj: BlockProps) => blockController.setBlockProps(obj)" />
				</div>
				<div v-else class="w-full py-4 text-center text-xs text-ink-gray-5">
					Select a block to preview data.
				</div>
			</div>
		</div>
		<div
			class="absolute bottom-0 left-0 box-border flex w-full items-center justify-between border-t bg-surface-white p-4 py-2">
			<h2 class="text-base text-ink-gray-6">Mode</h2>
			<TabButtons
				class="w-fit"
				:buttons="[
					{ label: 'Page', icon: 'layout', hideLabel: true, value: 'page', showTooltip: true },
					{ label: 'Block', icon: 'layers', hideLabel: true, value: 'block', showTooltip: true },
				]"
				v-model="mode" />
		</div>
		<Dialog
			class="overscroll-none"
			:options="{
				title:
					currentScriptEditor == 'data'
						? `${mode.charAt(0).toUpperCase() + mode.slice(1)} Data Script`
						: `${mode.charAt(0).toUpperCase() + mode.slice(1)} Client Script`,
				size: '7xl',
			}"
			:isDirty="isDirty"
			v-model="showDialog">
			<template #body-content>
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
					<div v-if="currentScriptEditor == 'client'">
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
					<div v-else>
						<div class="flex gap-4">
							<CodeEditor
								class="w-2/3 overscroll-none"
								ref="dataScriptEditor"
								v-model="blockDataScript"
								type="Python"
								mode="block"
								height="60vh"
								:readonly="builderStore.readOnlyMode"
								:autofocus="true"
								@save="saveBlockDataScript"
								:showSaveButton="true"
								:show-line-numbers="true"></CodeEditor>
							<CodeEditor
								v-model="blockData"
								type="JSON"
								label="Data Preview"
								:showLineNumbers="true"
								class="-mt-5 w-1/3 [&>div>div]:bg-surface-white"
								height="calc(100% - 110px)"
								description='Use Block Data Script to provide dynamic data to your block.<br>
								<b>Example:</b> block.events = frappe.get_list("Event")<br><br>
								For more details on how to write block data script, refer to <b><a class="underline" href="https://docs.frappe.io/builder/data-script" target="_blank">this documentation</a></b>.
								'
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
import { posthog } from "@/telemetry";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { computed, defineComponent, ref, watch } from "vue";
import { toast } from "vue-sonner";
import CodeEditor from "./Controls/CodeEditor.vue";
import PageClientScriptManager from "./PageClientScriptManager.vue";
import blockController from "@/utils/blockController";
import TabButtons from "./Controls/TabButtons.vue";
import Switch from "./Controls/Switch.vue";
import PropsEditor from "./PropsEditor.vue";
import useBlockDataStore from "@/stores/blockDataStore";

const pageStore = usePageStore();
const builderStore = useBuilderStore();
const blockDataStore = useBlockDataStore();

const showDialog = ref(false);
const mode = ref<"page" | "block">("block");
const showCumulativeBlockData = ref(false);

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

const blockDataScript = computed(() => {
	if (isBlockSelected.value) {
		return blockController.getFirstSelectedBlock()?.getBlockDataScript() || "";
	}
	return "";
});

const blockData = computed(() => {
	return isBlockSelected.value
		? blockDataStore.getBlockData(
				blockController.getFirstSelectedBlock().blockId,
				showCumulativeBlockData.value ? "all" : "own",
		  ) || {}
		: {};
});

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

const saveBlockClientScript = (value: string) => {
	if (isBlockSelected.value) {
		blockController.getFirstSelectedBlock()?.setBlockClientScript(value);
	}
};

const saveBlockDataScript = (value: string) => {
	if (isBlockSelected.value) {
		blockController.getFirstSelectedBlock()?.setBlockDataScript(value);
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
