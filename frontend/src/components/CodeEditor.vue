<template>
	<h3 class="mb-1 mt-8 text-xs font-bold uppercase text-gray-600">
		{{ label }}
	</h3>
	<div ref="editor" class="border border-gray-200 dark:border-zinc-800" />
</template>
<script setup lang="ts">
import { useDark } from "@vueuse/core";
import ace from "ace-builds";
import "ace-builds/src-noconflict/theme-chrome";
import "ace-builds/src-noconflict/theme-monokai";
import { PropType, onMounted, ref, watch, watchEffect } from "vue";
const isDark = useDark();

const props = defineProps({
	modelValue: {
		type: [Object, String, Array],
		required: true,
	},
	type: {
		type: String as PropType<"JSON" | "HTML">,
		default: "JSON",
	},
	label: {
		type: String,
		default: "",
	},
});

const emit = defineEmits(["update:modelValue"]);

const editor = ref<HTMLElement | null>(null);
onMounted(() => {
	let initialValue = props.modelValue;
	const aceEditor = ace.edit(editor.value!);
	aceEditor.setOptions({
		fontSize: "12px",
		useWorker: false,
		showGutter: false,
	});
	if (props.type === "JSON") {
		import("ace-builds/src-noconflict/mode-json").then(() => {
			aceEditor.session.setMode("ace/mode/json");
		});
		// check if initial value is valid json convert it to string
		try {
			initialValue = JSON.stringify(initialValue, null, 2);
		} catch (e) {
			// do nothing
		}
	} else {
		import("ace-builds/src-noconflict/mode-html").then(() => {
			aceEditor.session.setMode("ace/mode/html");
		});
	}
	aceEditor.setValue(initialValue as string);
	aceEditor.on("blur", () => {
		try {
			let value = aceEditor.getValue();
			if (props.type === "JSON") {
				value = JSON.parse(value);
			}
			emit("update:modelValue", value);
		} catch (e) {
			// do nothing
		}
	});
	watch(
		isDark,
		() => {
			aceEditor.setTheme(isDark.value ? "ace/theme/monokai" : "ace/theme/chrome");
		},
		{ immediate: true }
	);

	watchEffect(() => {
		let value = props.modelValue;
		if (props.type === "JSON") {
			value = JSON.stringify(value, null, 2);
		}
		aceEditor.setValue(value as string);
	});
});
</script>
<style scoped>
:deep(.ace_editor) {
	height: 200px;
	width: 100%;
	border-radius: 5px;
	overscroll-behavior: none;
}
:deep(.ace_scrollbar) {
	display: none;
}
</style>
