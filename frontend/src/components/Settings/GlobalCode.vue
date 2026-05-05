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
			:showLineNumbers="true"
			:externalEditorContext="getEditorContext('head_html')"></CodeEditor>
		<CodeEditor
			label="<body> HTML"
			type="HTML"
			description="Added to end of body. For adding scripts."
			:modelValue="builderSettings.doc?.body_html"
			height="100px"
			class="shrink-0"
			@update:modelValue="builderStore.updateBuilderSettings('body_html', $event)"
			:showLineNumbers="true"
			:externalEditorContext="getEditorContext('body_html')"></CodeEditor>
		<CodeEditor
			label="Client Script"
			type="JavaScript"
			description="This script will be executed on all the pages of your website."
			:modelValue="builderSettings.doc?.script"
			height="100px"
			class="shrink-0"
			@update:modelValue="(code) => builderStore.updateBuilderSettings('script', code)"
			:showLineNumbers="true"
			:externalEditorContext="getEditorContext('script')"></CodeEditor>
		<CodeEditor
			label="Style"
			type="CSS"
			description="Applies to all pages"
			:modelValue="builderSettings.doc?.style"
			height="100px"
			class="shrink-0"
			@update:modelValue="(code) => builderStore.updateBuilderSettings('style', code)"
			:showLineNumbers="true"
			:externalEditorContext="getEditorContext('style')"></CodeEditor>
	</div>
</template>
<script setup lang="ts">
import CodeEditor from "@/components/Controls/CodeEditor.vue";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import { createEditorContext } from "@/composables/useExternalEditor";

const builderStore = useBuilderStore();

const getEditorContext = (field: string) => {
	return createEditorContext("Builder Settings", "Builder Settings", field);
};
</script>
