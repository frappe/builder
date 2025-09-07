<script setup lang="ts">
import { ref, onMounted, watch } from "vue";

import { EditorView } from "codemirror";
import { oneDark } from "@codemirror/theme-one-dark";

import { useDark } from "@vueuse/core";
import { createResource } from "frappe-ui";
import { createStartingState } from "@/utils/createCodeMirrorState";
import { Compartment, EditorState } from "@codemirror/state";

const props = defineProps<{
	type: "Python" | "JavaScript" | "HTML" | "CSS" | "JSON";
	initialValue?: string;
	readonly: boolean;
	allowSave: boolean;
	showLineNumbers: boolean;
}>();

const editorContainer = ref<HTMLDivElement | null>(null);
const editor = ref<EditorView | null>(null);
const themeRef = ref<Compartment>();

const emit = defineEmits<{
	(e: "change"): void;
	(e: "save"): void;
}>();

const isDark = useDark({
	attribute: "data-theme",
});

const getPythonCompletions = async () => {
	let completionsResource = createResource({
		url: "builder.api.get_codemirror_completions",
		method: "GET",
	});
	await completionsResource.fetch();
	return completionsResource.data || {};
};

const resetEditor = async (params: { content: string; resetHistory: boolean; autofocus: boolean }) => {
	if (editor.value) {
		if (params.resetHistory) {
			editor.value.setState(
				(
					await createStartingState(
						props,
						await getPythonCompletions(),
						() => emit("save"),
						() => emit("change"),
						params.content,
					)
				).startState,
			);
		} else {
			editor.value.dispatch({
				changes: {
					from: 0,
					to: editor.value.state.doc.length,
					insert: params.content,
				},
			});
		}
		params.autofocus && editor.value.focus();
	} else {
		console.error("Editor not available!");
	}
};

watch(
	() => props.type,
	async (newType) => {
		console.log(newType, "changed type");
		editor.value?.destroy();

		if (editorContainer.value) {
			const { startState, theme } = await createStartingState(
				props,
				await getPythonCompletions(),
				() => emit("save"),
				() => emit("change"),
			);
			editor.value = new EditorView({
				state: startState,
				parent: editorContainer.value,
			});
			themeRef.value = theme;
		} else {
			console.error("Editor container not found");
		}
	},
);

watch(isDark, (newVal) => {
	if (editor.value) {
		editor.value.dispatch({
			effects: themeRef.value?.reconfigure(newVal ? oneDark : []),
		});
	}
});

onMounted(async () => {
	if (editorContainer.value) {
		const { startState, theme } = await createStartingState(
			props,
			await getPythonCompletions(),
			() => emit("save"),
			() => emit("change"),
		);
		editor.value = new EditorView({
			state: startState,
			parent: editorContainer.value,
		});
		themeRef.value = theme;
	} else {
		console.error("Editor container not found");
	}
});

defineExpose({
	editor,
	resetEditor,
});
</script>

<template>
	<div class="code-mirror-editor" style="height: 100%" ref="editorContainer"></div>
</template>

<style>
.code-mirror-editor {
	height: 100%;
	width: 100%;
	border-radius: 5px;
	overscroll-behavior: none;
}

.cm-editor {
	height: 100%;
	width: 100%;
}

.cm-focused {
	outline: none !important;
}
</style>
