<template>
	<div
		class="absolute bottom-0 z-50 h-fit w-full border-t border-gray-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
		<PanelResizer
			side="top"
			:dimension="store.builderLayout.scriptEditorHeight"
			:minDimension="100"
			:maxDimension="600"
			@resize="store.builderLayout.scriptEditorHeight = $event"></PanelResizer>
		<div
			class="flex gap-3"
			:style="{
				height: store.builderLayout.scriptEditorHeight + 'px',
			}">
			<div class="flex flex-col gap-3">
				<div class="pt-2 text-xs font-bold uppercase text-gray-600">Client Scripts</div>
				<div class="flex w-56 flex-col gap-1">
					<a
						v-for="script in attachedScriptResource.data"
						href="#"
						:class="{
							'text-gray-600 dark:text-gray-300': activeScript !== script,
							'font-medium dark:text-zinc-200': activeScript === script,
						}"
						@click="selectScript(script)"
						class="group flex items-center justify-between gap-1 text-sm">
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
					<div class="flex gap-2">
						<Dropdown
							:options="[
								{ label: 'JavaScript', onClick: () => addScript('JavaScript') },
								{ label: 'CSS', onClick: () => addScript('CSS') },
							]"
							size="sm"
							placement="right">
							<template v-slot="{ open }">
								<Button
									class="mt-2 w-full text-xs dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
									@click="open">
									New Script
								</Button>
							</template>
						</Dropdown>
						<Dropdown
							v-if="clientScriptResource.data && clientScriptResource.data.length > 0"
							:options="
								clientScriptResource.data.map((d: {'name': string}) => {
									return {
										label: d.name,
										onClick: () => {
											attachScript(d.name);
										},
									};
								})
							"
							size="sm"
							placement="right">
							<template v-slot="{ open }">
								<Button
									class="mt-2 w-full text-xs dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
									@click="open">
									Attach Script
								</Button>
							</template>
						</Dropdown>
					</div>
				</div>
			</div>
			<div
				class="flex h-full w-full items-center justify-center rounded bg-gray-100 text-base text-gray-600 dark:bg-zinc-800 dark:text-zinc-500"
				v-show="!activeScript">
				Select Script
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
	</div>
</template>
<script setup lang="ts">
import useStore from "@/store";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { Dropdown, createListResource, createResource } from "frappe-ui";
import { PropType, ref, watch } from "vue";
import CodeEditor from "./CodeEditor.vue";
import CSSIcon from "./Icons/CSS.vue";
import JavaScriptIcon from "./Icons/JavaScript.vue";
import PanelResizer from "./PanelResizer.vue";

type attachedScript = {
	script: string;
	script_type: string;
	name: string;
	script_name: string;
	editable: boolean;
};
const store = useStore();
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
});

const clientScriptResource = createListResource({
	doctype: "Builder Client Script",
	fields: ["script", "script_type", "name"],
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
	}
);
</script>
<style scoped>
:deep(.editor > .ace_editor) {
	border-top-left-radius: 0;
	border-top-right-radius: 0;
}
</style>
