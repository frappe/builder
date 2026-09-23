<template>
	<CodeEditor v-model="model" :extensions :autofocus @change="emit('change')">
		<CodeEditorContent class="code-mirror-editor w-full @container/editor" />
	</CodeEditor>
</template>
<script setup lang="ts">
import codeCompletions from "@/data/codeCompletions";
import useBuilderStore from "@/stores/builderStore";
import blockController from "@/utils/blockController";
import { getDefaultPropsList, getParentProps } from "@/utils/helpers";
import jsCompletionsFromGlobalScope from "@/utils/jsGlobalCompletion";
import customPythonCompletions from "@/utils/pythonCustomCompletion";
import type { CompletionSource } from "@codemirror/autocomplete";
import { EditorState } from "@codemirror/state";
import { EditorView, keymap } from "@codemirror/view";
import { indentationMarkers } from "@replit/codemirror-indentation-markers";
import { computedAsync } from "@vueuse/core";
import { CodeEditor, CodeEditorContent, CodeKit, loadLanguage } from "frappe-ui/code-editor";
import { computed, createApp } from "vue";
import CustomSearchPanel from "./CustomSearchPanel.vue";

type CodeType = "Python" | "JavaScript" | "HTML" | "CSS" | "JSON";

const model = defineModel<string>({ required: true });

const props = defineProps<{
	type: CodeType;
	mode?: "block" | "page" | "component";
	readonly: boolean;
	showLineNumbers: boolean;
	autofocus: boolean;
}>();

const emit = defineEmits<{
	change: [];
	save: [];
}>();

const builderStore = useBuilderStore();

const blockProps = computed(() => {
	const currentBlock = blockController.getFirstSelectedBlock();
	if (!currentBlock || typeof currentBlock.getBlockProps !== "function") return {};

	return {
		...getDefaultPropsList(currentBlock),
		...getParentProps(currentBlock),
		...currentBlock.getBlockProps(),
	};
});

const completionSources: Partial<Record<CodeType, CompletionSource>> = {
	JavaScript: (context) =>
		jsCompletionsFromGlobalScope(context, props.mode === "block" ? blockProps.value : {}),
	Python: (context) => customPythonCompletions(context, codeCompletions.data || {}),
};

function createSearchPanel(view: EditorView) {
	const dom = document.createElement("div");
	dom.classList.add("@container");
	const app = createApp(CustomSearchPanel);
	app.provide("view", view);
	app.provide("enableReplace", !props.readonly);
	app.mount(dom);
	return { dom, top: true, destroy: () => app.unmount() };
}

const staticExtensions = [
	indentationMarkers({
		colors: {
			light: "var(--outline-gray-2)",
			dark: "var(--outline-gray-2)",
			activeLight: "var(--outline-gray-4)",
			activeDark: "var(--outline-gray-4)",
		},
	}),
	keymap.of([
		{
			key: "Mod-s",
			run: () => {
				emit("save");
				return true;
			},
		},
	]),
];

const kit = computed(() =>
	CodeKit.configure({
		lineNumbers: props.showLineNumbers ? {} : false,
		search: { createPanel: createSearchPanel },
	}),
);

const language = computedAsync(() => loadLanguage(props.type.toLowerCase()), null);

const completions = computed(() => {
	const source = completionSources[props.type];
	return source ? EditorState.languageData.of(() => [{ autocomplete: source }]) : [];
});

const extensions = computed(() => [
	kit.value,
	language.value ?? [],
	completions.value,
	props.showLineNumbers ? EditorView.lineWrapping : [],
	// not :editable, a non-editable view can't take focus and loses Cmd-F search
	EditorState.readOnly.of(props.readonly),
	// selection colours key off this; the frappe chrome doesn't theme them
	EditorView.darkTheme.of(builderStore.isDark),
	...staticExtensions,
]);
</script>

<style>
/* the search panel floats over the first lines */
.code-mirror-editor .cm-editor:has(.cm-panels-top) .cm-content {
	padding-top: 5rem;
}

@container editor (min-width: 28rem) {
	.code-mirror-editor .cm-editor:has(.cm-panels-top) .cm-content {
		padding-top: 2.5rem;
	}
}
</style>
