<template>
	<div class="no-scrollbar flex flex-col gap-5 overflow-auto">
		<CodeEditor
			label="<head> HTML"
			type="HTML"
			description="Added to end of head. For meta tags, styles, and scripts."
			:modelValue="builderSettings.doc?.head_html"
			height="100px"
			class="shrink-0"
			@update:modelValue="builderStore.updateBuilderSettings('head_html', $event)"
			:showLineNumbers="true"></CodeEditor>
		<CodeEditor
			label="<body> HTML"
			type="HTML"
			description="Added to end of body. For adding scripts."
			:modelValue="builderSettings.doc?.body_html"
			height="100px"
			class="shrink-0"
			@update:modelValue="builderStore.updateBuilderSettings('body_html', $event)"
			:showLineNumbers="true"></CodeEditor>
		<CodeEditor
			label="Client Script"
			type="JavaScript"
			description="This script will be executed on all the pages of your website."
			:modelValue="builderSettings.doc?.script"
			height="100px"
			class="shrink-0"
			@update:modelValue="builderStore.updateBuilderSettings('script', $event)"
			:showLineNumbers="true"></CodeEditor>
		<CodeEditor
			label="Style"
			type="CSS"
			description="Applies to all pages"
			:modelValue="builderSettings.doc?.style"
			height="100px"
			class="shrink-0"
			@update:modelValue="builderStore.updateBuilderSettings('style', $event)"
			:showLineNumbers="true"></CodeEditor>
	</div>
</template>
<script setup lang="ts">
import CodeEditor from "@/components/Controls/CodeEditor.vue";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";

const builderStore = useBuilderStore();
</script>
