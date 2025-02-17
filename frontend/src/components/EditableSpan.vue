<template>
	<div
		ref="editableRef"
		:contenteditable="editMode"
		@dblclick="handleDoubleClick"
		@blur="handleBlur"
		@keydown="handleKeydown">
		<slot></slot>
	</div>
</template>

<script lang="ts" setup>
import { nextTick, ref, watch } from "vue";

const props = withDefaults(
	defineProps<{
		modelValue?: string;
		editable?: boolean;
	}>(),
	{
		modelValue: "",
		editable: false,
	},
);

const emit = defineEmits<{
	(e: "update:modelValue", value: string): void;
	(e: "change", value: string): void;
}>();

const editMode = ref(false);
const editableRef = ref<HTMLElement>();

function handleDoubleClick() {
	editMode.value = true;
}

function handleBlur() {
	editMode.value = false;
	const text = editableRef.value?.innerText.trim() ?? "";
	if (text === props.modelValue) return;
	if (!text) {
		editableRef.value!.innerText = props.modelValue!;
		return;
	}
	emit("update:modelValue", text);
	emit("change", text);
}

function handleKeydown(e: KeyboardEvent) {
	if (e.key === "Enter" && !e.shiftKey) {
		e.preventDefault();
		editableRef.value?.blur();
	}
	if (e.key === "Escape") {
		e.preventDefault();
		editableRef.value?.blur();
	}
}

watch(
	() => editMode.value,
	(value) => {
		nextTick(() => {
			if (value && editableRef.value) {
				editableRef.value?.focus();
				const range = document.createRange();
				range.selectNodeContents(editableRef.value);
				range.collapse(false);
				const selection = window.getSelection();
				selection?.removeAllRanges();
				selection?.addRange(range);
			}
		});
	},
);

watch(
	() => props.editable,
	(value) => {
		editMode.value = value;
	},
	{ immediate: true },
);
</script>
