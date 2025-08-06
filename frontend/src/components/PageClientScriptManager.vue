<template>
	<div class="flex gap-5">
		<div class="flex flex-col gap-3 pt-6">
			<div class="flex h-full w-48 flex-col justify-between gap-1">
				<div class="flex flex-col gap-1">
					<a
						v-for="script in attachedScriptResource.data"
						href="#"
						:class="{
							'text-ink-gray-5': activeScript !== script,
							'font-medium text-ink-gray-8': activeScript === script,
						}"
						@click="selectScript(script)"
						class="group flex h-6 items-center justify-between gap-1 text-sm last-of-type:mb-2">
						<div class="flex w-[90%] items-center gap-1">
							<CSSIcon class="shrink-0" v-if="script.script_type === 'CSS'" />

							<JavaScriptIcon class="shrink-0" v-if="script.script_type === 'JavaScript'" />

							<EditableSpan
								v-model="script.script_name"
								:editable="script.editable"
								:onChange="
									async (newName) => {
										await updateScriptName(newName, script);
									}
								"
								class="w-full truncate">
								{{ script.script_name }}
							</EditableSpan>
						</div>

						<Dropdown
							class="script-options"
							placement="right"
							v-if="activeScript === script"
							:options="[
								{
									label: 'Rename',
									onClick: () => {
										script.editable = true;
									},
									icon: 'edit',
								},
								{
									label: 'Remove Script',
									onClick: () => deleteScript(script.name),
									icon: 'trash',
								},
							]">
							<template v-slot="{ open }">
								<BuilderButton icon="more-horizontal" size="sm" variant="ghost" @click="open"></BuilderButton>
							</template>
						</Dropdown>
					</a>

					<div class="flex w-full gap-2">
						<Dropdown
							:options="[
								{ label: 'JavaScript', onClick: () => addScript('JavaScript') },
								{ label: 'CSS', onClick: () => addScript('CSS') },
							]"
							size="sm"
							class="flex-1 [&>div>div>div]:w-full">
							<template v-slot="{ open }">
								<BuilderButton class="w-full text-xs" @click="open">New Script</BuilderButton>
							</template>
						</Dropdown>

						<Autocomplete
							v-if="clientScriptResource.data && clientScriptResource.data.length > 0"
							:options="clientScriptOptions"
							class="[&>div>div>div]:overflow-hidden"
							@update:modelValue="(option: Option) => attachScript(option.value)"
							placeholder="Attach Script">
							<template v-slot:target="{ open }">
								<BuilderButton class="w-full text-xs" @click="open">Attach Script</BuilderButton>
							</template>
						</Autocomplete>
					</div>
				</div>

				<div class="text-xs leading-4 text-ink-gray-6">
					<b>Note:</b>
					All client scripts are executed in preview mode and on published pages.
				</div>
			</div>
		</div>

		<div
			class="flex h-[70vh] w-full items-center justify-center rounded bg-surface-gray-1 text-base text-ink-gray-6"
			v-show="!activeScript">
			Add Script
		</div>

		<div v-if="activeScript" class="flex h-full w-full flex-col">
			<CodeEditor
				ref="scriptEditor"
				:modelValue="activeScript.script"
				:label="activeScript.script_name"
				:type="activeScript.script_type as 'JavaScript' | 'CSS'"
				class="flex-1"
				height="65vh"
				:autofocus="false"
				:show-save-button="true"
				@save="updateScript"
				:show-line-numbers="true"></CodeEditor>
		</div>
	</div>
</template>

<script setup lang="ts">
import EditableSpan from "@/components/EditableSpan.vue";
import usePageStore from "@/stores/pageStore";
import { posthog } from "@/telemetry";
import { BuilderClientScript } from "@/types/Builder/BuilderClientScript";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { Autocomplete, createListResource, createResource, Dropdown } from "frappe-ui";
import { computed, nextTick, ref, watch } from "vue";
import { toast } from "vue-sonner";
import CodeEditor from "./Controls/CodeEditor.vue";
import CSSIcon from "./Icons/CSS.vue";
import JavaScriptIcon from "./Icons/JavaScript.vue";

const scriptEditor = ref<InstanceType<typeof CodeEditor> | null>(null);
const pageStore = usePageStore();

type attachedScript = {
	script: string;
	script_type: string;
	name: string;
	script_name: string;
	editable: boolean;
};

type Option = {
	label: string;
	value: string;
};

const activeScript = ref<attachedScript | null>(null);

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
		"builder_script.script",
		"builder_script.script_type",
		"builder_script.name as script_name",
		"name",
	],
	orderBy: "`tabBuilder Page Client Script`.idx asc",
	auto: true,
	onSuccess: (data: attachedScript[]) => {
		if (data && data.length > 0 && !activeScript.value) {
			selectScript(data[0]);
		}
	},
});

const clientScriptResource = createListResource({
	doctype: "Builder Client Script",
	fields: ["script", "script_type", "name"],
	pageLength: 500,
	auto: true,
});

const selectScript = (script: attachedScript) => {
	activeScript.value = script;
	nextTick(() => {
		scriptEditor.value?.resetEditor(true);
	});
};

const updateScript = (value: string) => {
	if (!activeScript.value) return;

	pageStore.activePageScripts = pageStore.activePageScripts.map((script: BuilderClientScript) => {
		if (script.name === activeScript.value?.script_name) {
			script.script = value;
		}
		return script;
	});

	clientScriptResource.setValue
		.submit({
			name: activeScript.value.script_name,
			script: value,
		})
		.then(async () => {
			await attachedScriptResource.reload();
			attachedScriptResource.data?.forEach((script: attachedScript) => {
				if (script.script_name === activeScript.value?.script_name) {
					activeScript.value = script;
				}
			});
			toast.success("Script saved successfully");
		})
		.catch((e: { message: string; exc: string }) => {
			const error_message = e.exc.split("\n").slice(-2)[0];
			toast.error("Failed to save script", {
				description: error_message,
			});
		});
};

const addScript = (scriptType: "JavaScript" | "CSS") => {
	clientScriptResource.insert
		.submit({
			script_type: scriptType,
			script: scriptType === "JavaScript" ? "// Write your script here\n" : "/* Write your CSS here */\n",
		})
		.then((res: BuilderClientScript) => {
			attachedScriptResource.insert
				.submit({
					parent: props.page.name,
					parenttype: "Builder Page",
					parentfield: "client_scripts",
					builder_script: res.name,
				})
				.then(async () => {
					posthog.capture("builder_client_script_added", {
						script_type: res.script_type,
					});
					await attachedScriptResource.reload();
					attachedScriptResource.data?.forEach((script: attachedScript) => {
						if (script.script_name === res.name) {
							selectScript(script);
						}
					});
					pageStore.activePageScripts.push(res);
				});
		});
};

const attachScript = (builder_script_name: string) => {
	attachedScriptResource.insert
		.submit({
			parent: props.page.name,
			parenttype: "Builder Page",
			parentfield: "client_scripts",
			builder_script: builder_script_name,
		})
		.then(async () => {
			posthog.capture("builder_client_script_attached");
			await attachedScriptResource.reload();
			attachedScriptResource.data?.forEach((script: attachedScript) => {
				if (script.script_name === builder_script_name) {
					selectScript(script);
				}
			});
		});
};

const deleteScript = (scriptName: string) => {
	activeScript.value = null;
	attachedScriptResource.delete.submit(scriptName).then(() => {
		attachedScriptResource.reload();
	});
	pageStore.activePageScripts = pageStore.activePageScripts.filter(
		(script: BuilderClientScript) => script.name !== scriptName,
	);
};

const updateScriptName = async (newName: string, script: attachedScript) => {
	if (!newName) return;
	script.editable = false;
	pageStore.activePageScripts = pageStore.activePageScripts.map((_script: BuilderClientScript) => {
		if (_script.name === script.name) {
			script.name = newName;
		}
		return script;
	});
	return createResource({
		url: "frappe.client.rename_doc",
	})
		.submit({
			doctype: "Builder Client Script",
			old_name: script?.script_name,
			new_name: newName,
		})
		.then(async () => {
			attachedScriptResource.data = attachedScriptResource.data.map(
				(s: { script_name: string; script: string }) => {
					if (s.script_name === script.script_name) {
						s.script_name = newName;
					}
					return s;
				},
			);
		});
};

const clientScriptOptions = computed(() =>
	clientScriptResource.data?.map((script: { name: string; script_type: string }) => ({
		label: `${script.name}.${script.script_type == "JavaScript" ? "js" : script.script_type.toLowerCase()}`,
		value: script.name,
	})),
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

defineExpose({ scriptEditor });
</script>

<style scoped>
:deep(.editor > .ace_editor) {
	border-top-left-radius: 0;
	border-top-right-radius: 0;
}
</style>
