<template>
	<div
		class="absolute bottom-0 z-50 h-fit w-full border-t border-gray-200 bg-white p-2 py-3 dark:border-zinc-700 dark:bg-zinc-900">
		<PanelResizer
			side="top"
			:dimension="store.builderLayout.scriptEditorHeight"
			:minDimension="100"
			:maxDimension="600"
			@resize="store.builderLayout.scriptEditorHeight = $event"></PanelResizer>
		<div class="flex gap-3">
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
						<div class="flex items-center gap-1">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="18"
								height="18"
								viewBox="0 0 256 256"
								v-if="script.script_type === 'CSS'">
								<path
									fill="currentColor"
									d="M48 180c0 11 7.18 20 16 20a14.24 14.24 0 0 0 10.22-4.66a8 8 0 1 1 11.55 11.06A30 30 0 0 1 64 216c-17.65 0-32-16.15-32-36s14.35-36 32-36a30 30 0 0 1 21.77 9.6a8 8 0 1 1-11.55 11.06A14.24 14.24 0 0 0 64 160c-8.82 0-16 9-16 20Zm79.6-8.69c-4-1.16-8.14-2.35-10.45-3.84c-1.26-.81-1.23-1-1.12-1.9a4.54 4.54 0 0 1 2-3.67c4.6-3.12 15.34-1.73 19.83-.56a8 8 0 0 0 4.07-15.48c-2.12-.55-21-5.22-32.83 2.76a20.55 20.55 0 0 0-9 14.95c-2 15.88 13.64 20.41 23 23.11c12.07 3.49 13.13 4.92 12.78 7.59c-.31 2.41-1.26 3.34-2.14 3.93c-4.6 3.06-15.17 1.56-19.55.36a8 8 0 0 0-4.3 15.41a61.23 61.23 0 0 0 15.18 2c5.83 0 12.3-1 17.49-4.46a20.82 20.82 0 0 0 9.19-15.23c2.25-17.28-14.27-22.11-24.15-24.97Zm64 0c-4-1.16-8.14-2.35-10.45-3.84c-1.25-.81-1.23-1-1.12-1.9a4.54 4.54 0 0 1 2-3.67c4.6-3.12 15.34-1.73 19.82-.56a8 8 0 0 0 4.07-15.48c-2.11-.55-21-5.22-32.83 2.76a20.58 20.58 0 0 0-8.95 14.95c-2 15.88 13.65 20.41 23 23.11c12.06 3.49 13.12 4.92 12.78 7.59c-.31 2.41-1.26 3.34-2.15 3.93c-4.6 3.06-15.16 1.56-19.54.36a8 8 0 0 0-4.3 15.44a61.34 61.34 0 0 0 15.19 2c5.82 0 12.3-1 17.49-4.46a20.81 20.81 0 0 0 9.18-15.23c2.21-17.31-14.31-22.14-24.2-25ZM40 112V40a16 16 0 0 1 16-16h96a8 8 0 0 1 5.66 2.34l56 56A8 8 0 0 1 216 88v24a8 8 0 1 1-16 0V96h-48a8 8 0 0 1-8-8V40H56v72a8 8 0 0 1-16 0Zm120-32h28.68L160 51.31Z" />
							</svg>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="18"
								height="18"
								viewBox="0 0 256 256"
								v-if="script.script_type === 'JavaScript'">
								<path
									fill="currentColor"
									d="m213.66 82.34l-56-56A8 8 0 0 0 152 24H56a16 16 0 0 0-16 16v72a8 8 0 0 0 16 0V40h88v48a8 8 0 0 0 8 8h48v120h-24a8 8 0 0 0 0 16h24a16 16 0 0 0 16-16V88a8 8 0 0 0-2.34-5.66ZM160 51.31L188.69 80H160Zm-12.19 145a20.82 20.82 0 0 1-9.19 15.23C133.43 215 127 216 121.13 216a61.34 61.34 0 0 1-15.19-2a8 8 0 0 1 4.31-15.41c4.38 1.2 15 2.7 19.55-.36c.88-.59 1.83-1.52 2.14-3.93c.34-2.67-.71-4.1-12.78-7.59c-9.35-2.7-25-7.23-23-23.11a20.56 20.56 0 0 1 9-14.95c11.84-8 30.71-3.31 32.83-2.76a8 8 0 0 1-4.07 15.48c-4.49-1.17-15.23-2.56-19.83.56a4.54 4.54 0 0 0-2 3.67c-.12.9-.14 1.09 1.11 1.9c2.31 1.49 6.45 2.68 10.45 3.84c9.84 2.83 26.4 7.66 24.16 24.97ZM80 152v38a26 26 0 0 1-52 0a8 8 0 0 1 16 0a10 10 0 0 0 20 0v-38a8 8 0 0 1 16 0Z" />
							</svg>
							<span>
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
								<Button class="mt-2 w-full text-xs" @click="open">Add</Button>
							</template>
						</Dropdown>
						<Dropdown
							v-if="clientScriptResource.data && clientScriptResource.data.length > 0"
							:options="
								clientScriptResource.data.map((d) => {
									console.log(d);
									return {
										label: d.name,
										onClick: () => {
											attachedScriptResource.insert
												.submit({
													parent: props.page.name,
													parenttype: 'Builder Page',
													parentfield: 'client_scripts',
													builder_script: d.name,
												})
												.then(() => {
													attachedScriptResource.reload();
												});
										},
									};
								})
							"
							size="sm"
							placement="right">
							<template v-slot="{ open }">
								<Button class="mt-2 w-full text-xs" @click="open">Attach</Button>
							</template>
						</Dropdown>
					</div>
				</div>
			</div>
			<div
				class="flex min-h-[400px] w-full items-center justify-center rounded bg-gray-100 text-base text-gray-600 dark:bg-zinc-800 dark:text-zinc-500"
				v-show="!activeScript">
				Select Script
			</div>
			<div v-if="activeScript" class="w-full">
				<span class="rounded-t-sm bg-gray-100 p-1 px-2 text-xs dark:bg-zinc-800 dark:text-zinc-100">
					{{ activeScript.script_name }}
				</span>
				<CodeEditor
					v-if="activeScript.script_type === 'JavaScript'"
					:modelValue="activeScript.script"
					@update:modelValue="updateScript"
					type="JavaScript"
					:height="store.builderLayout.scriptEditorHeight + 'px'"
					:show-line-numbers="true"></CodeEditor>
				<CodeEditor
					v-if="activeScript.script_type === 'CSS'"
					:modelValue="activeScript.script"
					@update:modelValue="updateScript"
					type="CSS"
					:height="store.builderLayout.scriptEditorHeight + 'px'"
					:show-line-numbers="true"></CodeEditor>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import useStore from "@/store";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { createListResource, Dropdown } from "frappe-ui";
import { PropType, ref } from "vue";
import CodeEditor from "./CodeEditor.vue";
import PanelResizer from "./PanelResizer.vue";

type attachedScript = {
	script: string;
	script_type: string;
	name: string;
	script_name: string;
};
const activeScript = ref<attachedScript | null>(null);

const selectScript = (script: attachedScript) => {
	activeScript.value = script;
};

const store = useStore();

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
});

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
						console.log(script.script_name, res.name);
						if (script.script_name === res.name) {
							selectScript(script);
						}
					});
				});
		});
};

const deleteScript = (scriptName: string) => {
	activeScript.value = null;
	attachedScriptResource.delete.submit(scriptName).then(() => {
		attachedScriptResource.reload();
	});
};
</script>
