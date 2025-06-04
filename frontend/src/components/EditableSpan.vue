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
import { toast } from "vue-sonner";

const props = withDefaults(
	defineProps<{
		modelValue?: string;
		editable?: boolean;
		onChange?: (value: string) => Promise<void>;
	}>(),
	{
		modelValue: "",
		editable: false,
	},
);

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
		editableRef.value!.innerText = props.modelValue;
		return;
	}
	if (props.onChange) {
		props.onChange(text).catch((e) => {
			let error_message = e.exc.split("\n").slice(-2)[0];
			if (error_message.includes("Duplicate") || error_message.includes("select another name")) {
				error_message = "Name already exists";
			}
			toast.error("Failed to rename", {
				description: error_message,
			});
			editableRef.value!.innerText = props.modelValue;
		});
	}
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
