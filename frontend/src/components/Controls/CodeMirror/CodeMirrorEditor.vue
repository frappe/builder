<template>
	<div
		class="code-mirror-editor relative @container/editor"
		ref="editorContainer"
		@keydown="handleKeyDown"></div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import codeCompletions from "@/data/codeCompletions";
import { createStartingState } from "@/utils/createCodeMirrorState";
import { openSearchPanel } from "@codemirror/search";
import { Compartment } from "@codemirror/state";
import { oneDark } from "@codemirror/theme-one-dark";
import { useDark } from "@vueuse/core";
import { EditorView } from "codemirror";
import { tomorrow } from "thememirror";
import blockController from "@/utils/blockController";
import { getDefaultPropsList, getParentProps } from "@/utils/helpers";

const props = defineProps<{
	type: "Python" | "JavaScript" | "HTML" | "CSS" | "JSON";
	mode?: "block" | "page";
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
	(e: "blur", value: string): void;
}>();

const isDark = useDark({
	attribute: "data-theme",
});

const getPythonCompletions = async () => {
	return codeCompletions.data || {};
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
						onBlurCallback: (value: string) => emit("blur", value),
						initialValue: params.content,
						extraExtensions: [theme.of(isDark.value ? oneDark : tomorrow)],
						mode: props.mode,
						blockProps: allBlockProps.value,
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
		(editor.dom.querySelector(".cm-content") as HTMLElement)?.classList.remove("@md/editor:!pt-10", "!pt-20");
	}
};

const handleKeyDown = (e: KeyboardEvent) => {
	if ((e.ctrlKey || e.metaKey) && e.key === "f") {
		e.stopImmediatePropagation();
		e.preventDefault();
		const closestCmEditor = (e?.target as HTMLElement)?.closest(".cm-editor") as HTMLElement;
		const closestCmContent = closestCmEditor.querySelector(".cm-content") as HTMLElement;
		closestCmContent?.classList.add("@md/editor:!pt-10", "!pt-20");
		if (editor) {
			openSearchPanel(editor);
		}
	}
};

watch(isDark, (newVal) => {
	if (editor) {
		editor.dispatch({
			effects: theme.reconfigure(newVal ? oneDark : tomorrow),
		});
	}
});

const allBlockProps = computed(() => {
	const currentBlock = blockController.getFirstSelectedBlock();
	if (currentBlock) {
		const ownBlockProps = currentBlock.getBlockProps();
		const inheritedBlockProps = getParentProps(currentBlock, {});
		const defaultProps = getDefaultPropsList(currentBlock, blockController);
		return {
			...defaultProps,
			...inheritedBlockProps,
			...ownBlockProps,
		};
	}
});

onMounted(async () => {
	if (editorContainer.value) {
		const { startState } = await createStartingState({
			props,
			pythonCompletions: await getPythonCompletions(),
			onSaveCallback: () => emit("save", getEditorValue()),
			onChangeCallback: () => emit("change", getEditorValue()),
			onBlurCallback: (value: string) => emit("blur", value),
			extraExtensions: [theme.of(isDark.value ? oneDark : tomorrow)],
			mode: props.mode,
			blockProps: allBlockProps.value,
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
	background-color: rgb(190 190 190 / 15%) !important;
}

.cm-editor {
	background-color: var(--surface-gray-1, #ffffff) !important;
}

.cm-gutters {
	background-color: var(--surface-gray-2) !important;
	border: none;
}

.cm-activeLineGutter {
	background-color: var(--surface-gray-4) !important;
}

.cm-gutters {
	color: var(--ink-gray-4) !important;
}
/* TODO make the search bar better looking */
</style>
