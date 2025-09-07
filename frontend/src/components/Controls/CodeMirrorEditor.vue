<script setup lang="ts">
import { ref, onMounted, watch } from "vue";

import { EditorView } from "codemirror";
import { oneDark } from "@codemirror/theme-one-dark";
import { tomorrow } from "thememirror";
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
let editor: EditorView | null = null;
const theme = new Compartment();

const emit = defineEmits<{
	(e: "change", value: string): void;
	(e: "save", value: string): void;
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

const getEditorValue = () => {
	if (editor) {
		return editor.state.doc.toString();
	}
	return "";
};

const resetEditor = async (params: { content: string; resetHistory: boolean; autofocus: boolean }) => {
	if (editor) {
		if (params.resetHistory) {
			editor.setState(
				(
					await createStartingState({
						props,
						pythonCompletions: await getPythonCompletions(),
						onSaveCallback: () => emit("save", getEditorValue()),
						onChangeCallback: () => emit("change", getEditorValue()),
						initialValue: params.content,
						extraExtensions: [theme.of(isDark.value ? oneDark : tomorrow)],
					})
				).startState,
			);
		} else {
			editor.dispatch({
				changes: {
					from: 0,
					to: editor.state.doc.length,
					insert: params.content,
				},
			});
		}
		params.autofocus && editor.focus();
	} else {
		console.error("Editor not available!");
	}
};

// watch(
// 	() => props.type,
// 	async (newType) => {
// 		editor?.destroy();

// 		if (editorContainer.value) {
// 			const { startState } = await createStartingState({
// 				props,
// 				pythonCompletions: await getPythonCompletions(),
// 				onSaveCallback: () => emit("save"),
// 				onChangeCallback: () => emit("change"),
// 				extraExtensions: [theme.of(isDark.value ? oneDark : tomorrow)],
// 			});
// 			editor = new EditorView({
// 				state: startState,
// 				parent: editorContainer.value,
// 			});
// 		} else {
// 			console.error("Editor container not found");
// 		}
// 	},
// );

watch(isDark, (newVal) => {
	if (editor) {
		editor.dispatch({
			effects: theme.reconfigure(newVal ? oneDark : tomorrow),
		});
	}
});

onMounted(async () => {
	if (editorContainer.value) {
		const { startState } = await createStartingState({
			props,
			pythonCompletions: await getPythonCompletions(),
			onSaveCallback: () => emit("save", getEditorValue()),
			onChangeCallback: () => emit("change", getEditorValue()),
			extraExtensions: [theme.of(isDark.value ? oneDark : tomorrow)],
		});
		editor = new EditorView({
			state: startState,
			parent: editorContainer.value,
		});
	} else {
		console.error("Editor container not found");
	}
});

defineExpose({
	resetEditor,
	getEditorValue,
});
</script>

<template>
	<div class="code-mirror-editor" ref="editorContainer"></div>
</template>

<style>
.code-mirror-editor {
	width: 100%;
	border-radius: 5px;
	overscroll-behavior: none;
	display: flex;
	flex: 1;
}

.cm-editor {
	height: 100%;
	width: 100%;
	flex: 1;
}

.cm-focused {
	outline: none !important;
}

.cm-activeLine {
	background-color: rgb(191 191 191 / 16%) !important;
}

/* TODO make the search bar better looking */
</style>
