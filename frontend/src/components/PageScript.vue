<template>
	<div
		class="absolute bottom-0 z-50 h-fit w-full border-t border-gray-200 bg-white p-2 dark:border-zinc-700 dark:bg-gray-900">
		<PanelResizer
			side="top"
			:dimension="store.builderLayout.scriptEditorHeight"
			:minDimension="100"
			:maxDimension="600"
			@resize="store.builderLayout.scriptEditorHeight = $event"></PanelResizer>
		<div class="flex flex-col gap-1">
			<TabButtons
				class="w-fit [&>div>button[aria-checked='false']]:dark:!bg-transparent [&>div>button[aria-checked='false']]:dark:!text-zinc-400 [&>div>button[aria-checked='true']]:dark:!bg-zinc-700 [&>div>button]:dark:!bg-zinc-700 [&>div>button]:dark:!text-zinc-100 [&>div]:dark:!bg-zinc-800"
				:buttons="[
					{ label: 'Script', value: 'script' },
					{ label: 'Style', value: 'style' },
				]"
				:modelValue="activeTab"
				@update:modelValue="activeTab = $event"></TabButtons>
			<CodeEditor
				v-show="activeTab === 'script'"
				:modelValue="page.client_script"
				@update:modelValue="save('client_script', $event)"
				type="JavaScript"
				:height="store.builderLayout.scriptEditorHeight + 'px'"
				:show-line-numbers="true"></CodeEditor>
			<CodeEditor
				v-show="activeTab === 'style'"
				:modelValue="page.style"
				@update:modelValue="save('style', $event)"
				type="CSS"
				:height="store.builderLayout.scriptEditorHeight + 'px'"
				:show-line-numbers="true"></CodeEditor>
		</div>
	</div>
</template>
<script setup lang="ts">
import { webPages } from "@/data/webPage";
import useStore from "@/store";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { TabButtons } from "frappe-ui";
import { PropType, ref } from "vue";
import CodeEditor from "./CodeEditor.vue";
import PanelResizer from "./PanelResizer.vue";

const activeTab = ref("script");

const store = useStore();

const props = defineProps({
	page: {
		type: Object as PropType<BuilderPage>,
		required: true,
	},
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
</script>
