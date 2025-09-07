<template>
	<div class="code-editor relative flex flex-col gap-1">
		<span class="text-p-sm font-medium text-ink-gray-8" v-show="label">
			{{ label }}
			<span v-if="isDirty" class="text-[10px] text-gray-600">●</span>
		</span>
		<div v-if="actionButton" class="absolute bottom-1.5 right-1.5 z-10 flex gap-1">
			<BuilderButton
				@click="actionButton?.handler"
				variant="subtle"
				class="!h-6 !w-6 border !border-outline-gray-2 bg-surface-white [&>svg]:!h-3.5 [&>svg]:!w-3.5"
				:icon="actionButton.icon"
				:title="actionButton.label"></BuilderButton>
		</div>
		<div
			:style="{
				'min-height': height,
			}"
			class="h-auto resize-y overflow-hidden overscroll-none !rounded border border-outline-gray-2 bg-surface-gray-2 dark:bg-gray-900">
			<CodeMirrorEditor
				ref="editor"
				:type
				:readonly
				:allow-save="showSaveButton"
				:show-line-numbers
				:initial-value="getModelValue()"
				@change="handleChange"
				@save="handleSave" />
		</div>
		<span class="mt-1 text-p-xs text-ink-gray-6" v-show="description" v-html="description"></span>
		<BuilderButton
			v-if="showSaveButton"
			variant="solid"
			@click="emit('save', getEditorValue())"
			class="mt-3"
			:disabled="!isDirty">
			Save
		</BuilderButton>
	</div>
</template>
<script setup lang="ts">
import { useDark } from "@vueuse/core";
// import ace from "ace-builds";
// import "ace-builds/src-min-noconflict/ext-searchbox";
// import "ace-builds/src-min-noconflict/theme-chrome";
// import "ace-builds/src-min-noconflict/theme-twilight";
import { ref, watch } from "vue";
import CodeMirrorEditor from "./CodeMirrorEditor.vue";
import { VNodeRef } from "vue";

const isDark = useDark({
	attribute: "data-theme",
});
const props = withDefaults(
	defineProps<{
		modelValue?: Object | String | Array<any>;
		type?: "JSON" | "HTML" | "Python" | "JavaScript" | "CSS";
		label?: string;
		readonly?: boolean;
		height?: string;
		showLineNumbers?: boolean;
		autofocus?: boolean;
		showSaveButton?: boolean;
		description?: string;
		actionButton?: {
			label: string;
			icon: string;
			handler: () => void;
		};
	}>(),
	{
		type: "JSON",
		label: "",
		readonly: false,
		height: "250px",
		showLineNumbers: false,
		autofocus: true,
		showSaveButton: false,
		description: "",
	},
);

const emit = defineEmits(["save", "update:modelValue"]);
const editor = ref<VNodeRef | null>(null);

const isDirty = ref(false);

// TODO: implemet onBlur event for codemirror
// aceEditor.on("blur", () => {
// 	try {
// 		let value = getEditorValue();
// 		if (value === getModelValue()) return;
// 		if (!props.showSaveButton && !props.readonly) {
// 			emit("update:modelValue", value);
// 		}
// 	} catch (e) {
// 		// do nothing
// 	}
// });

const getModelValue = () => {
	let value = props.modelValue ?? "";
	try {
		if (props.type === "JSON" || typeof value === "object") {
			value = JSON.stringify(value, null, 2);
		}
	} catch (e) {
		// do nothing
	}
	return value as string;
};

const getEditorValue = () => {
	if (editor.value && editor.value.editor) {
		let value = editor.value.editor.state.doc.toString();
		if (props.type === "JSON" && value) {
			value = JSON.parse(value);
		}
		return value;
	}
};

const handleChange = () => {
	if (getEditorValue() === getModelValue()) {
		isDirty.value = false;
		return;
	} else if (!props.readonly) {
		isDirty.value = true;
	}
};

const handleSave = () => {
	const value = getEditorValue();
	if (props.showSaveButton) {
		emit("save", value);
	} else {
		emit("update:modelValue", value);
	}
};

function resetEditor(resetHistory = false) {
	const value = getModelValue();
	if (editor.value && editor.value.resetEditor) {
		// reset from inside the editor component to avoid recreating state
		editor.value.resetEditor({ content: value, resetHistory, autofocus: props.autofocus });
		isDirty.value = false;
	} else {
		console.error("Editor not available!");
	}
	// aceEditor?.clearSelection(); // TODO: implement in codemirror
	isDirty.value = false;
}

watch(
	() => props.modelValue,
	() => {
		resetEditor();
	},
);

defineExpose({ resetEditor, isDirty });
</script>
