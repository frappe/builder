<template>
	<div class="no-scrollbar flex flex-col gap-5 overflow-auto">
		<CodeEditor
			label="<head> HTML"
			type="HTML"
			description="添加到 head 末尾。用于 meta 标签、样式和脚本。"
			:modelValue="builderSettings.doc?.head_html"
			height="100px"
			class="shrink-0"
			@update:modelValue="builderStore.updateBuilderSettings('head_html', $event)"
			:showLineNumbers="true"></CodeEditor>
		<CodeEditor
			label="<body> HTML"
			type="HTML"
			description="添加到 body 末尾。用于添加脚本。"
			:modelValue="builderSettings.doc?.body_html"
			height="100px"
			class="shrink-0"
			@update:modelValue="builderStore.updateBuilderSettings('body_html', $event)"
			:showLineNumbers="true"></CodeEditor>
		<CodeEditor
			label="客户端脚本"
			type="JavaScript"
			description="该脚本将在您网站的所有页面上执行。"
			:modelValue="builderSettings.doc?.script"
			height="100px"
			class="shrink-0"
			@update:modelValue="(code) => builderStore.updateBuilderSettings('script', code)"
			:showLineNumbers="true"></CodeEditor>
		<CodeEditor
			label="样式"
			type="CSS"
			description="应用于所有页面"
			:modelValue="builderSettings.doc?.style"
			height="100px"
			class="shrink-0"
			@update:modelValue="(code) => builderStore.updateBuilderSettings('style', code)"
			:showLineNumbers="true"></CodeEditor>
	</div>
</template>
<script setup lang="ts">
import CodeEditor from "@/components/Controls/CodeEditor.vue";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";

const builderStore = useBuilderStore();
</script>
