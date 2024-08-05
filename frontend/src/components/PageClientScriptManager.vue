<template>
	<div class="flex h-[70vh] gap-5">
		<div class="flex flex-col gap-3">
			<div class="flex h-full w-48 flex-col justify-between gap-1">
				<div class="flex flex-col gap-1">
					<a
						v-for="script in attachedScriptResource.data"
						href="#"
						:class="{
							'text-gray-600 dark:text-gray-300': activeScript !== script,
							'font-medium dark:text-zinc-200': activeScript === script,
						}"
						@click="selectScript(script)"
						class="group flex items-center justify-between gap-1 text-sm last-of-type:mb-2">
						<div class="flex w-[90%] items-center gap-1">
							<CSSIcon class="shrink-0" v-if="script.script_type === 'CSS'" />
							<JavaScriptIcon class="shrink-0" v-if="script.script_type === 'JavaScript'" />
							<span
								class="truncate"
								@blur="updateScriptName($event, script)"
								@keydown.enter.stop.prevent="script.editable = false"
								@dblclick="script.editable = true"
								:contenteditable="script.editable">
								{{ script.script_name }}
							</span>
						</div>
						<FeatherIcon name="trash" class="h-3 w-3" @click.stop="deleteScript(script.name)"></FeatherIcon>
					</a>
					<div class="flex w-full gap-2">
						<Dropdown
							:options="[
								{ label: 'JavaScript', onClick: () => addScript('JavaScript') },
								{ label: 'CSS', onClick: () => addScript('CSS') },
							]"
							size="sm"
							class="flex-1 [&>div>div>div]:w-full"
							placement="right">
							<template v-slot="{ open }">
								<Button
									class="w-full text-xs dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
									@click="open">
									New Script
								</Button>
							</template>
						</Dropdown>
						<Dropdown
							v-if="clientScriptResource.data && clientScriptResource.data.length > 0"
							:options="
								clientScriptResource.data.map((d: { name: string }) => {
									return {
										label: d.name,
										onClick: () => {
											attachScript(d.name);
										},
									};
								})
							"
							size="sm"
							class="max-w-60 flex-1 [&>div>div>div]:w-full">
							<template v-slot="{ open }">
								<Button
									class="w-full text-xs dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
									@click="open">
									Attach Script
								</Button>
							</template>
						</Dropdown>
					</div>
				</div>
				<div class="text-xs text-gray-600 dark:text-zinc-300">
					<b>Note:</b>
					All client scripts are executed in preview mode and on published pages.
				</div>
			</div>
		</div>
		<div
			class="flex h-full w-full items-center justify-center rounded bg-gray-100 text-base text-gray-600 dark:bg-zinc-900 dark:text-zinc-500"
			v-show="!activeScript">
			Add Script
		</div>
		<div v-if="activeScript" class="flex h-full w-full flex-col">
			<span class="rounded-t-sm bg-gray-100 p-1 px-2 text-xs dark:bg-zinc-800 dark:text-zinc-100">
				{{ activeScript.script_name }}
			</span>
			<CodeEditor
				v-if="activeScript.script_type === 'JavaScript'"
				:modelValue="activeScript.script"
				@update:modelValue="updateScript"
				type="JavaScript"
				class="flex-1"
				height="auto"
				:show-line-numbers="true"></CodeEditor>
			<CodeEditor
				v-if="activeScript.script_type === 'CSS'"
				:modelValue="activeScript.script"
				@update:modelValue="updateScript"
				type="CSS"
				class="flex-1"
				height="auto"
				:show-line-numbers="true"></CodeEditor>
		</div>
	</div>
</template>
<script setup lang="ts">
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { Dropdown, createListResource, createResource } from "frappe-ui";
import posthog from "posthog-js";
import { PropType, ref, watch } from "vue";
import CodeEditor from "./CodeEditor.vue";
import CSSIcon from "./Icons/CSS.vue";
import JavaScriptIcon from "./Icons/JavaScript.vue";

type attachedScript = {
	script: string;
	script_type: string;
	name: string;
	script_name: string;
	editable: boolean;
};

const activeScript = ref<attachedScript | null>(null);

const props = defineProps({
	page: {
		type: Object as PropType<BuilderPage>,
		required: true,
	},
});

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
	orderBy: "`tabBuilder Page Client Script`.creation asc",
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
	pageLength: 100,
	auto: true,
});

const selectScript = (script: attachedScript) => {
	activeScript.value = script;
};

const updateScript = (value: string) => {
	if (!activeScript.value) return;
	clientScriptResource.setValue
		.submit({
			name: activeScript.value.script_name,
			script: value,
		})
		.then(() => {
			attachedScriptResource.reload();
		});
};

const addScript = (scriptType: "JavaScript" | "CSS") => {
	clientScriptResource.insert
		.submit({
			script_type: scriptType,
			script: scriptType === "JavaScript" ? "// Write your script here\n" : "/* Write your CSS here */\n",
		})
		.then((res: { name: string; script_type: string; script: string }) => {
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
};

const updateScriptName = (ev: Event, script: attachedScript) => {
	const target = ev.target as HTMLElement;
	const newName = target.innerText.trim();
	createResource({
		url: "frappe.client.rename_doc",
	})
		.submit({
			doctype: "Builder Client Script",
			old_name: script?.script_name,
			new_name: newName,
		})
		.then(async () => {
			await attachedScriptResource.reload();
			await clientScriptResource.reload();
			attachedScriptResource.data?.forEach((script: attachedScript) => {
				if (script.script_name === newName) {
					selectScript(script);
				}
			});
		});
};

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
</script>
<style scoped>
:deep(.editor > .ace_editor) {
	border-top-left-radius: 0;
	border-top-right-radius: 0;
}
</style>
