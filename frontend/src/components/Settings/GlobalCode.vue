<template>
	<div class="no-scrollbar flex flex-col gap-5 overflow-auto">
		<CodeEditor
			label="<head> HTML"
			type="HTML"
			description="Added to end of head. For meta tags, styles, and scripts."
			:modelValue="builderSettings.doc.head_html"
			height="150px"
			class="shrink-0"
			@update:modelValue="store.updateBuilderSettings('head_html', $event)"
			:showLineNumbers="true"></CodeEditor>
		<CodeEditor
			label="<body> HTML"
			type="HTML"
			description="Added to end of body. For adding scripts."
			:modelValue="builderSettings.doc.body_html"
			height="150px"
			class="shrink-0"
			@update:modelValue="store.updateBuilderSettings('body_html', $event)"
			:showLineNumbers="true"></CodeEditor>
		<CodeEditor
			label="Client Script"
			type="JavaScript"
			description="This script will be executed on all the pages of your website."
			:modelValue="builderSettings.doc.script"
			height="250px"
			class="shrink-0"
			@update:modelValue="store.updateBuilderSettings('script', $event)"
			:showLineNumbers="true"></CodeEditor>
		<CodeEditor
			label="Style"
			type="CSS"
			description="Applies to all pages"
			:modelValue="builderSettings.doc.style"
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
