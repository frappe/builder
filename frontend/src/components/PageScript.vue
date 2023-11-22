<template>
	<div
		class="absolute bottom-0 z-50 h-fit w-full border-t border-gray-200 bg-white p-2 dark:border-zinc-700 dark:bg-gray-900">
		<PanelResizer
			side="top"
			:dimension="store.builderLayout.scriptEditorHeight"
			:minDimension="100"
			:maxDimension="600"
			@resize="store.builderLayout.scriptEditorHeight = $event"></PanelResizer>
		<div class="text-xs font-bold uppercase text-gray-600">Client Script</div>
		<div class="flex gap-3 py-3">
			<div class="flex w-56 flex-col gap-1">
				<a
					v-for="script in listResource.data"
					href="#"
					:class="{
						'text-gray-600 dark:text-gray-300': activeScript !== script,
						'font-medium': activeScript === script,
					}"
					@click="selectScript(script)"
					class="flex items-center gap-1 text-sm">
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
						v-if="script.script_type === 'Javascript'">
						<path
							fill="currentColor"
							d="m213.66 82.34l-56-56A8 8 0 0 0 152 24H56a16 16 0 0 0-16 16v72a8 8 0 0 0 16 0V40h88v48a8 8 0 0 0 8 8h48v120h-24a8 8 0 0 0 0 16h24a16 16 0 0 0 16-16V88a8 8 0 0 0-2.34-5.66ZM160 51.31L188.69 80H160Zm-12.19 145a20.82 20.82 0 0 1-9.19 15.23C133.43 215 127 216 121.13 216a61.34 61.34 0 0 1-15.19-2a8 8 0 0 1 4.31-15.41c4.38 1.2 15 2.7 19.55-.36c.88-.59 1.83-1.52 2.14-3.93c.34-2.67-.71-4.1-12.78-7.59c-9.35-2.7-25-7.23-23-23.11a20.56 20.56 0 0 1 9-14.95c11.84-8 30.71-3.31 32.83-2.76a8 8 0 0 1-4.07 15.48c-4.49-1.17-15.23-2.56-19.83.56a4.54 4.54 0 0 0-2 3.67c-.12.9-.14 1.09 1.11 1.9c2.31 1.49 6.45 2.68 10.45 3.84c9.84 2.83 26.4 7.66 24.16 24.97ZM80 152v38a26 26 0 0 1-52 0a8 8 0 0 1 16 0a10 10 0 0 0 20 0v-38a8 8 0 0 1 16 0Z" />
					</svg>
					{{ script.name }}
				</a>
				<div class="flex gap-2">
					<Button class="mt-2 w-full" @click="addScript">Add</Button>
					<Button class="mt-2 w-full">Attach</Button>
				</div>
			</div>
			<div class="flex min-h-[300px] w-full items-center justify-center" v-show="!activeScript">
				Select Script
			</div>
			<CodeEditor
				v-if="activeScript && activeScript.script_type === 'Javascript'"
				class="w-full"
				:modelValue="activeScript.script"
				@update:modelValue="updateScript"
				type="JavaScript"
				:height="store.builderLayout.scriptEditorHeight + 'px'"
				:show-line-numbers="true"></CodeEditor>
			<CodeEditor
				v-if="activeScript && activeScript.script_type === 'CSS'"
				class="w-full"
				:modelValue="activeScript.script"
				@update:modelValue="updateScript"
				type="CSS"
				:height="store.builderLayout.scriptEditorHeight + 'px'"
				:show-line-numbers="true"></CodeEditor>
		</div>
	</div>
</template>
<script setup lang="ts">
import { webPages } from "@/data/webPage";
import useStore from "@/store";
import { BuilderClientScript } from "@/types/Builder/BuilderClientScript";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { createListResource } from "frappe-ui";
import { PropType, ref } from "vue";
import CodeEditor from "./CodeEditor.vue";
import PanelResizer from "./PanelResizer.vue";
import { getRandomColor } from "@/utils/helpers";

const activeScript = ref<BuilderClientScript | null>(null);

const selectScript = (script: BuilderClientScript) => {
	activeScript.value = script;
};

const store = useStore();

const props = defineProps({
	page: {
		type: Object as PropType<BuilderPage>,
		required: true,
	},
});

const listResource = createListResource({
	doctype: "Builder Page Client Script",
	parent: "Builder Page",
	filters: {
		parent: props.page.name,
	},
	fields: ["builder_script.script", "builder_script.script_type", "builder_script.name"],
	auto: true,
	onSuccess: (data) => {
		console.log(data);
	},
});

const documentResource = createListResource({
	doctype: "Builder Client Script",
});

const save = (type: "client_script" | "style", value: string) => {
	if (!props.page) return;
	webPages.setValue
		.submit({
			name: props.page.name,
			[type]: value,
		})
		.then(() => {
			store.setPageData();
		});
};

const updateScript = (value: string) => {
	if (!activeScript.value) return;
	documentResource.setValue
		.submit({
			name: activeScript.value.name,
			script: value,
		})
		.then(() => {
			listResource.reload();
		});
};

const addScript = () => {
	if (!props.page) return;
	documentResource.insert
		.submit({
			name: props.page.name,
			script_type: "Javascript",
			script: "// Write your script here",
		})
		.then(() => {
			// props.page.client_scripts?.push({
			// 	builder_script: props.page.name,
			// });
			// props.page.save();
			console.log(listResource.data, props.page);
			webPages.setValue
				.submit({
					name: props.page.name + getRandomColor(),
					client_scripts: [
						...(listResource.data || []),
						{
							builder_script: props.page.name,
						},
					],
				})
				.then(() => {
					listResource.reload();
				});
		});
};
</script>
