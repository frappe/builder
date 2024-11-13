<template>
	<div class="no-scrollbar flex flex-col gap-5 overflow-auto">
		<CodeEditor
			label="Client Script"
			type="JavaScript"
			description="Note: This script will be executed on all the pages of your website."
			:modelValue="builderSettings.doc?.script"
			height="250px"
			class="shrink-0"
			@update:modelValue="store.updateBuilderSettings('script', $event)"
			:showLineNumbers="true"></CodeEditor>
		<CodeEditor
			label="Style"
			type="CSS"
			description="Note: This style will be applied to all the pages of your website."
			:modelValue="builderSettings.doc?.style"
			height="250px"
			class="shrink-0"
			@update:modelValue="store.updateBuilderSettings('style', $event)"
			:showLineNumbers="true"></CodeEditor>
	</div>
</template>
<script setup lang="ts">
import CodeEditor from "@/components/Controls/CodeEditor.vue";
import { builderSettings } from "@/data/builderSettings";
import useStore from "@/store";

const store = useStore();
</script>
