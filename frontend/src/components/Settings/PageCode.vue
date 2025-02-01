<template>
	<div class="no-scrollbar flex flex-col gap-5 overflow-auto">
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
import CodeEditor from "@/components/Controls/CodeEditor.vue";
import useStore from "@/store";

const store = useStore();
</script>
