<template>
	<div class="no-scrollbar flex flex-col gap-6 overflow-auto">
		<div>
			<div class="">
				<InputLabel>Load Library</InputLabel>
				<div class="mb-2 flex">
					<BuilderInput class="w-full"></BuilderInput>
					<BuilderButton class="ml-2">Load</BuilderButton>
				</div>
			</div>
			<div class="flex flex-col gap-2">
				<div v-for="script in scripts" class="rounded bg-surface-gray-2 px-3 pr-0 shadow-sm">
					<div class="flex w-full items-center justify-between gap-2">
						<div class="flex items-center gap-2">
							<span class="text-ink-gray-4">{{ script.type }}</span>
							<a href="{{ script.script_url }}" class="text-sm hover:underline">{{ script.script_url }}</a>
						</div>
						<BuilderButton class="ml-2 text-sm">Remove</BuilderButton>
					</div>
				</div>
			</div>
		</div>
		<CodeEditor
			label="<head> code"
			type="HTML"
			description="Note: This will be appended to the end of head of all pages."
			height="250px"
			class="shrink-0"
			:modelValue="store.activePage?.head_script"
			@update:modelValue="(val) => store.updateActivePage('head_script', val)"
			:showLineNumbers="true"></CodeEditor>
	</div>
</template>
<script setup lang="ts">
import BuilderButton from "@/components/Controls/BuilderButton.vue";
import CodeEditor from "@/components/Controls/CodeEditor.vue";
import InputLabel from "@/components/Controls/InputLabel.vue";
import useStore from "@/store";
const store = useStore();

const scripts = [
	{
		type: "js",
		script_url: "https://cdn.jsdelivr.net/npm/vue@3.2.20/dist/vue.global.prod.js",
	},
	{
		type: "css",
		script_url: "https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css",
	},
];
</script>
