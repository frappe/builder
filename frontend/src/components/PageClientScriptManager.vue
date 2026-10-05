<template>
	<div class="flex gap-5">
		<div class="flex flex-col gap-3">
			<div class="flex h-full w-48 flex-col justify-between gap-1">
				<div class="flex flex-col gap-1">
					<draggable
						v-model="attachedScripts"
						:item-key="(script: attachedScript) => script.name"
						handle=".drag-handle"
						@end="onScriptReorder"
						class="flex flex-col gap-1">
						<template #item="{ element: script }">
							<a
								href="#"
								:class="{
									'text-ink-gray-5': !isActive(script),
									'font-medium !text-ink-gray-8': isActive(script),
								}"
								@click="switchToScript(script)"
								class="group flex h-6 items-center justify-between gap-1 text-sm first-of-type:mt-6 last-of-type:mb-2 hover:text-ink-gray-7">
								<div class="flex w-[90%] items-center gap-1">
									<span
										class="drag-handle lucide-grip-vertical size-3.5 cursor-grab text-ink-gray-5 hover:text-ink-gray-8" />
									<CSSIcon class="shrink-0" v-if="script.script_type === 'CSS'" />

									<JavaScriptIcon class="shrink-0" v-if="script.script_type === 'JavaScript'" />

									<EditableSpan
										:key="script.script_name"
										v-model="script.script_name"
										:editable="script.editable && !builderStore.readOnlyMode"
										:onChange="(newName) => renameScript(newName, script)"
										@blur="script.editable = false"
										class="w-full truncate">
										{{ script.script_name }}
									</EditableSpan>
								</div>

								<Dropdown
									class="script-options"
									align="end"
									v-if="isActive(script) && !builderStore.readOnlyMode"
									:options="[
										{
											label: __('Rename'),
											onClick: () => {
												script.editable = true;
											},
											icon: 'lucide-edit',
										},
										{
											label: __('Remove Script'),
											onClick: () => removeScript(script),
											icon: 'lucide-trash',
										},
									]">
									<Button icon="lucide-more-horizontal" size="sm" variant="ghost" @click.stop></Button>
								</Dropdown>
							</a>
						</template>
					</draggable>

					<div
						class="grid w-full grid-cols-1 gap-2"
						v-if="!builderStore.readOnlyMode"
						:class="
							clientScriptResource.data && clientScriptResource.data.length > 0
								? 'grid-cols-2'
								: 'grid-cols-1'
						">
						<Dropdown
							:options="[
								{ label: __('JavaScript'), onClick: () => addScript('JavaScript') },
								{ label: __('CSS'), onClick: () => addScript('CSS') },
							]"
							size="sm"
							class="[&>div>div>div]:w-full">
							<template v-slot="{ open }">
								<Button class="w-full text-xs" @click="open">{{ __("New Script") }}</Button>
							</template>
						</Dropdown>

						<Combobox
							v-if="clientScriptResource.data && clientScriptResource.data.length > 0"
							:key="attachPickerKey"
							:options="clientScriptOptions"
							:placeholder="__('Attach Script')"
							@update:modelValue="onScriptSelected">
							<template #trigger>
								<Button class="w-full text-xs">{{ __("Attach Script") }}</Button>
							</template>
						</Combobox>
					</div>
				</div>

				<div class="text-xs leading-4 text-ink-gray-6">
					<b>{{ __("Note:") }}</b>
					{{ __("All client scripts are executed in preview mode and on published pages.") }}
				</div>
			</div>
		</div>

		<div
			class="flex h-[calc(65vh+68px)] w-full items-center justify-center rounded-4 border border-dashed border-outline-gray-2 bg-surface-gray-1 text-base text-ink-gray-6"
			v-show="!activeScript">
			{{ __("Add Script") }}
		</div>

		<div v-if="activeScript" class="flex h-full w-full flex-col">
			<CodeEditor
				ref="scriptEditor"
				:modelValue="activeScript.script"
				:label="activeScript.script_name"
				:type="activeScript.script_type as 'JavaScript' | 'CSS'"
				class="flex-1"
				mode="page"
				height="65vh"
				:readonly="builderStore.readOnlyMode"
				:autofocus="false"
				:show-save-button="true"
				@save="updateScript"
				:show-line-numbers="true">
				<template #label-suffix>
					<a
						v-if="!scriptUsageResource.loading"
						@click="pageListDialog = true"
						class="ml-1 cursor-pointer text-p-sm text-ink-gray-4 underline">
						{{ usageMessage }}
					</a>
				</template>
			</CodeEditor>
		</div>
		<PageListModal v-model="pageListDialog" :pages="scriptUsedInPages"></PageListModal>
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import EditableSpan from "@/components/EditableSpan.vue";
import PageListModal from "@/components/Modals/PageListModal.vue";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { BuilderClientScript, BuilderPage, BuilderPageClientScript } from "@/types/doctypes";
import { promptDiscardScriptEdits, promptScriptConflict, promptSharedScriptSave } from "@/utils/dialogs";
import { getErrorMessage, getPageUsageMessage } from "@/utils/helpers";
import { Combobox, createListResource, createResource, Dropdown, type ComboboxOptionValue } from "frappe-ui";
import { useTelemetry } from "@framework/ui/telemetry";
import { computed, nextTick, ref, watch } from "vue";
import { toast } from "frappe-ui";
import draggable from "vuedraggable";
import CodeEditor from "./Controls/CodeEditor.vue";
import CSSIcon from "./Icons/CSS.vue";
import JavaScriptIcon from "./Icons/JavaScript.vue";

const { capture } = useTelemetry();

const scriptEditor = ref<InstanceType<typeof CodeEditor> | null>(null);
const builderStore = useBuilderStore();
const pageStore = usePageStore();

type attachedScript = {
	name: string;
	creation: string;
	modified: string;
	owner: string;
	modified_by: string;
	script_name: string;
	script: string;
	script_type: string;
	script_public_url?: string;
	script_creation: string;
	script_modified: string;
	script_owner: string;
	script_modified_by: string;
	editable: boolean;
};

const activeScript = ref<attachedScript | null>(null);
// rows are matched by name: the list refetches on its own after insert/delete, swapping every object
const isActive = (script: attachedScript) => activeScript.value?.name === script.name;

const props = defineProps<{
	page: BuilderPage;
}>();

const attachedScriptResource = createListResource({
	doctype: "Builder Page Client Script",
	parent: "Builder Page",
	filters: {
		parent: props.page.name,
	},
	fields: [
		"name",
		"creation",
		"modified",
		"owner",
		"modified_by",
		"builder_script.name as script_name",
		"builder_script.script",
		"builder_script.script_type",
		"builder_script.public_url as script_public_url",
		"builder_script.creation as script_creation",
		"builder_script.modified as script_modified",
		"builder_script.owner as script_owner",
		"builder_script.modified_by as script_modified_by",
	],
	orderBy: "`tabBuilder Page Client Script`.idx asc",
	auto: true,
	onSuccess: (data: attachedScript[]) => {
		syncPageStore(data);
		const pendingName = builderStore.openClientScript;
		if (pendingName) {
			builderStore.openClientScript = null;
			const target = data.find((s: attachedScript) => s.script_name === pendingName);
			if (target) {
				selectScript(target);
				return;
			}
		}
		if (data && data.length > 0 && !activeScript.value) {
			selectScript(data[0]);
		}
	},
});

const attachedScripts = computed({
	get: (): attachedScript[] => attachedScriptResource.data ?? [],
	set: (scripts: attachedScript[]) => {
		attachedScriptResource.data = scripts;
	},
});

// copy/paste and the AI read the page's scripts from the store, so it mirrors this list
const syncPageStore = (scripts: attachedScript[]) => {
	const page = pageStore.activePage;
	// a reply can land after another page opened, and that page may share these scripts
	if (page?.name !== props.page.name) return;
	page.client_scripts = scripts.map(toPageRow);
	pageStore.activePageScripts = scripts.map(toScriptDoc);
};

const toPageRow = (script: attachedScript, index: number): BuilderPageClientScript => ({
	name: script.name,
	creation: script.creation,
	modified: script.modified,
	owner: script.owner,
	modified_by: script.modified_by,
	parent: props.page.name,
	parenttype: "Builder Page",
	parentfield: "client_scripts",
	idx: index + 1,
	builder_script: script.script_name,
});

const toScriptDoc = (script: attachedScript): BuilderClientScript => ({
	name: script.script_name,
	creation: script.script_creation,
	modified: script.script_modified,
	owner: script.script_owner,
	modified_by: script.script_modified_by,
	script: script.script,
	script_type: script.script_type,
	public_url: script.script_public_url,
});

// a reload swaps every row object, so re-point whatever is selected once it lands (the user may
// have switched meanwhile), following `moved` when the selected script was renamed or copied
const reloadScripts = async (moved?: { from: string; to: string }) => {
	await attachedScriptResource.reload();
	let name = activeScript.value?.script_name;
	if (moved && name === moved.from) name = moved.to;
	activeScript.value = attachedScripts.value.find((s) => s.script_name === name) ?? null;
};

const clientScriptResource = createListResource({
	doctype: "Builder Client Script",
	fields: ["script_type", "name"],
	pageLength: 10000,
	auto: true,
});

const pageListDialog = ref(false);

const usagePageLimit = 100;

const scriptUsageResource = createListResource({
	doctype: "Builder Page",
	fields: ["name", "page_title", "route", "preview"],
	pageLength: usagePageLimit,
});

const scriptUsedInPages = computed<BuilderPage[]>(() => scriptUsageResource.data ?? []);
const otherPagesLabel = computed(() => {
	const count = scriptUsedInPages.value.length;
	return count === usagePageLimit ? `${usagePageLimit - 1}+` : String(count - 1);
});
const usageMessage = computed(() => {
	const count = scriptUsedInPages.value.length;
	return count === usagePageLimit
		? __("used in {0}+ pages", [usagePageLimit - 1])
		: getPageUsageMessage(count);
});

const loadUsage = (scriptName: string) => {
	scriptUsageResource.filters = [["Builder Page Client Script", "builder_script", "=", scriptName]];
	scriptUsageResource.reload();
};

const selectScript = (script: attachedScript) => {
	activeScript.value = script;
	loadUsage(script.script_name);
	nextTick(() => {
		scriptEditor.value?.resetEditor(true);
	});
};

const switchToScript = async (script: attachedScript) => {
	if (script.name === activeScript.value?.name) return;
	const current = activeScript.value?.script_name ?? "";
	if (scriptEditor.value?.isDirty && !(await promptDiscardScriptEdits(current))) return;
	selectScript(script);
};

const updateScript = async (value: string) => {
	const target = activeScript.value;
	if (!target || builderStore.readOnlyMode) return;

	if (!value || !value.trim()) {
		toast.warning(__("Script cannot be empty"));
		return;
	}

	if (scriptUsageResource.list.loading) await scriptUsageResource.list.promise;
	// usage now describes the current selection, and switching scripts already dropped this edit
	if (activeScript.value?.script_name !== target.script_name) return;
	if (scriptUsedInPages.value.length > 1) {
		const choice = await promptSharedScriptSave(target.script_name, otherPagesLabel.value);
		if (choice === "copy") return saveScriptAsCopy(target, value);
		if (choice !== "all") return;
	}
	saveScript(target, value);
};

const saveScript = async (target: attachedScript, value: string, overwrite = false): Promise<void> => {
	try {
		await createResource({ url: "builder.api.save_client_script" }).submit({
			name: target.script_name,
			script: value,
			modified: overwrite ? undefined : target.script_modified,
		});
	} catch (error) {
		return onSaveFailed(target, value, error);
	}
	await reloadScripts();
	toast.success(__("Script saved successfully"));
};

const onSaveFailed = async (target: attachedScript, value: string, error: unknown): Promise<void> => {
	if (!isStaleSave(error)) {
		toast.error(__("Failed to save script"), { description: getErrorMessage(error) });
		return;
	}
	const choice = await promptScriptConflict(target.script_name);
	if (choice === "overwrite") return saveScript(target, value, true);
	if (choice !== "reload") return;
	await reloadScripts();
	if (activeScript.value) selectScript(activeScript.value);
};

const isStaleSave = (error: unknown) =>
	typeof error === "object" &&
	error !== null &&
	"exc_type" in error &&
	error.exc_type === "TimestampMismatchError";

const saveScriptAsCopy = async (source: attachedScript, value: string) => {
	const pageName = props.page.name;
	try {
		const copyName: string = await createResource({ url: "builder.api.save_client_script_as_copy" }).submit({
			page_name: pageName,
			script_name: source.script_name,
			script: value,
		});
		await reloadScripts({ from: source.script_name, to: copyName });
		if (activeScript.value?.script_name === copyName) loadUsage(copyName);
		clientScriptResource.reload();
		toast.success(__("Saved as {0} for this page", [copyName]));
	} catch (error) {
		toast.error(__("Failed to save script"), { description: getErrorMessage(error) });
	}
};

const addScript = async (scriptType: "JavaScript" | "CSS") => {
	if (builderStore.readOnlyMode) return;
	try {
		// builder_client_script_created is captured in the backend (before_insert)
		const script: BuilderClientScript = await clientScriptResource.insert.submit({
			script_type: scriptType,
			script: scriptType === "JavaScript" ? "// Write your script here\n" : "/* Write your CSS here */\n",
		});
		await attachToPage(script.name);
	} catch (error) {
		toast.error(__("Failed to add script"), { description: getErrorMessage(error) });
	}
};

// the picker keeps its last pick, so picking the same script again later would not fire
const attachPickerKey = ref(0);

const onScriptSelected = (value: ComboboxOptionValue | null | undefined) => {
	attachPickerKey.value++;
	if (typeof value === "string" && value) attachScript(value);
};

const attachScript = async (scriptName: string) => {
	if (builderStore.readOnlyMode) return;
	try {
		await attachToPage(scriptName);
		capture("builder_client_script_attached");
	} catch (error) {
		toast.error(__("Failed to attach script"), { description: getErrorMessage(error) });
	}
};

const attachToPage = async (scriptName: string) => {
	await attachedScriptResource.insert.submit({
		parent: props.page.name,
		parenttype: "Builder Page",
		parentfield: "client_scripts",
		builder_script: scriptName,
	});
	await reloadScripts();
	const attached = attachedScripts.value.find((s) => s.script_name === scriptName);
	if (attached) await switchToScript(attached);
};

const removeScript = async (script: attachedScript) => {
	if (builderStore.readOnlyMode) return;
	try {
		await attachedScriptResource.delete.submit(script.name);
	} catch (error) {
		toast.error(__("Failed to remove script"), { description: getErrorMessage(error) });
		return;
	}
	await reloadScripts();
	if (!activeScript.value && attachedScripts.value.length) selectScript(attachedScripts.value[0]);
};

const renameScript = async (newName: string, script: attachedScript) => {
	if (!newName || builderStore.readOnlyMode) return;
	await createResource({ url: "frappe.client.rename_doc" }).submit({
		doctype: "Builder Client Script",
		old_name: script.script_name,
		new_name: newName,
	});
	await reloadScripts({ from: script.script_name, to: newName });
	if (activeScript.value?.script_name === newName) loadUsage(newName);
	clientScriptResource.reload();
};

const clientScriptOptions = computed(() => {
	const attached = new Set(attachedScripts.value.map((script) => script.script_name));
	return (clientScriptResource.data ?? [])
		.filter((script: { name: string }) => !attached.has(script.name))
		.map((script: { name: string; script_type: string }) => ({
			label: `${script.name}.${script.script_type == "JavaScript" ? "js" : script.script_type.toLowerCase()}`,
			value: script.name,
		}));
});

const onScriptReorder = () => {
	syncPageStore(attachedScripts.value);
	createResource({
		url: "builder.api.reorder_client_scripts",
	})
		.submit({
			script_order: attachedScripts.value.map((script) => script.name),
		})
		.then(() => {
			toast.success(__("Script order updated"));
		})
		.catch((error: unknown) => {
			toast.error(__("Failed to update script order"), { description: getErrorMessage(error) });
			reloadScripts();
		});
};

const selectScriptByName = (name: string) => {
	const target = attachedScripts.value.find((s) => s.script_name === name);
	if (target) selectScript(target);
};

// Handle openClientScript when data is already loaded (component already mounted)
watch(
	() => builderStore.openClientScript,
	(name) => {
		if (!name || !attachedScriptResource.data?.length) return;
		builderStore.openClientScript = null;
		selectScriptByName(name);
	},
);

watch(
	() => props.page,
	async () => {
		activeScript.value = null;
		attachedScriptResource.filters.parent = props.page.name;
		await attachedScriptResource.reload();
		if (attachedScriptResource.data && attachedScriptResource.data.length > 0) {
			selectScript(attachedScriptResource.data[0]);
		}
	},
);

defineExpose({ scriptEditor, selectScriptByName });
</script>

<style scoped>
:deep(.editor > .ace_editor) {
	border-top-left-radius: 0;
	border-top-right-radius: 0;
}
</style>
