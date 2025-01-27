<template>
	<div
		class="editor flex flex-col gap-1"
		:style="{
			height: height,
		}">
		<span class="text-p-sm font-medium text-ink-gray-8" v-if="label">
			{{ label }}
			<span v-if="isDirty" class="text-[10px] text-gray-600">●</span>
		</span>
		<div
			ref="editor"
			class="h-auto flex-1 overflow-hidden overscroll-none !rounded border border-outline-gray-2 bg-surface-gray-2 dark:bg-gray-900" />
		<span class="mt-1 text-p-xs text-ink-gray-6" v-show="description" v-html="description"></span>
		<BuilderButton
			v-if="showSaveButton"
			@click="emit('save', aceEditor?.getValue())"
			class="mt-3"
			:disabled="!isDirty">
			Save
		</BuilderButton>
	</div>
</template>
<script setup lang="ts">
import { useDark } from "@vueuse/core";
import ace from "ace-builds";
import "ace-builds/src-min-noconflict/ext-searchbox";
import "ace-builds/src-min-noconflict/theme-chrome";
import "ace-builds/src-min-noconflict/theme-twilight";
import { PropType, onMounted, ref, watch } from "vue";

const isDark = useDark({
	attribute: "data-theme",
});
const props = defineProps({
	modelValue: {
		type: [Object, String, Array],
	},
	type: {
		type: String as PropType<"JSON" | "HTML" | "Python" | "JavaScript" | "CSS">,
		default: "JSON",
	},
	label: {
		type: String,
		default: "",
	},
	readonly: {
		type: Boolean,
		default: false,
	},
	height: {
		type: String,
		default: "250px",
	},
	showLineNumbers: {
		type: Boolean,
		default: false,
	},
	autofocus: {
		type: Boolean,
		default: true,
	},
	showSaveButton: {
		type: Boolean,
		default: false,
	},
	description: {
		type: String,
		default: "",
	},
});

const emit = defineEmits(["save", "update:modelValue"]);
const editor = ref<HTMLElement | null>(null);
let aceEditor = null as ace.Ace.Editor | null;

onMounted(() => {
	setupEditor();
});

const isDirty = ref(false);

const setupEditor = () => {
	aceEditor = ace.edit(editor.value as HTMLElement);
	resetEditor(props.modelValue as string, true);
	aceEditor.setReadOnly(props.readonly);
	aceEditor.setOptions({
		fontSize: "12px",
		useWorker: false,
		showGutter: props.showLineNumbers,
		wrap: props.showLineNumbers,
	});
	if (props.type === "CSS") {
		import("ace-builds/src-noconflict/mode-css").then(() => {
			aceEditor?.session.setMode("ace/mode/css");
		});
	} else if (props.type === "JavaScript") {
		import("ace-builds/src-noconflict/mode-javascript").then(() => {
			aceEditor?.session.setMode("ace/mode/javascript");
		});
	} else if (props.type === "Python") {
		import("ace-builds/src-noconflict/mode-python").then(() => {
			aceEditor?.session.setMode("ace/mode/python");
		});
	} else if (props.type === "JSON") {
		import("ace-builds/src-noconflict/mode-json").then(() => {
			aceEditor?.session.setMode("ace/mode/json");
		});
	} else {
		import("ace-builds/src-noconflict/mode-html").then(() => {
			aceEditor?.session.setMode("ace/mode/html");
		});
	}

	aceEditor.on("change", () => {
		if (aceEditor?.getValue() === props.modelValue) {
			isDirty.value = false;
			return;
		} else {
			isDirty.value = true;
		}
	});

	aceEditor.on("blur", () => {
		try {
			let value = aceEditor?.getValue() || "";
			if (props.type === "JSON") {
				value = JSON.parse(value);
			}
			if (value === props.modelValue) return;
			if (!props.showSaveButton && !props.readonly) {
				emit("update:modelValue", value);
			}
		} catch (e) {
			// do nothing
		}
	});
};

const getModelValue = () => {
	let value = props.modelValue || "";
	try {
		if (props.type === "JSON" || typeof value === "object") {
			value = JSON.stringify(value, null, 2);
		}
	} catch (e) {
		// do nothing
	}
	return value as string;
};

function resetEditor(value: string, resetHistory = false) {
	value = getModelValue();
	aceEditor?.setValue(value);
	aceEditor?.clearSelection();
	aceEditor?.setTheme(isDark.value ? "ace/theme/twilight" : "ace/theme/chrome");
	props.autofocus && aceEditor?.focus();
	if (resetHistory) {
		aceEditor?.session.getUndoManager().reset();
	}
}

watch(isDark, () => {
	aceEditor?.setTheme(isDark.value ? "ace/theme/twilight" : "ace/theme/chrome");
});

watch(
	() => props.type,
	() => {
		setupEditor();
	},
);

watch(
	() => props.modelValue,
	() => {
		resetEditor(props.modelValue as string);
	},
);

defineExpose({ resetEditor, isDirty });
</script>
<style scoped>
.editor .ace_editor {
	height: 100%;
	width: 100%;
	border-radius: 5px;
	overscroll-behavior: none;
}
.editor :deep(.ace_scrollbar-h) {
	display: none;
}
.editor :deep(.ace_search) {
	@apply dark:bg-gray-800 dark:text-gray-200;
	@apply dark:border-gray-800;
}
.editor :deep(.ace_searchbtn) {
	@apply dark:bg-gray-800 dark:text-gray-200;
	@apply dark:border-gray-800;
}
.editor :deep(.ace_button) {
	@apply dark:bg-gray-800 dark:text-gray-200;
}

.editor :deep(.ace_search_field) {
	@apply dark:bg-gray-900 dark:text-gray-200;
	@apply dark:border-gray-800;
}
</style>
