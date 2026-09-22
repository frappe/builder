<template>
	<div class="code-editor relative flex flex-col gap-1">
		<span class="text-p-sm-medium text-ink-gray-8" v-show="label">
			{{ label }}
			<span v-if="isDirty" class="text-[10px] text-gray-600">●</span>
			<slot name="label-suffix"></slot>
		</span>
		<!-- -m-0.5 p-0.5 keeps the focus ring clear of the overflow clip resize-y needs -->
		<div
			:style="{ minHeight: height }"
			class="-m-0.5 flex h-[30vh] max-h-[80vh] resize-y overflow-hidden p-0.5"
			@keydown.stop
			@copy.stop
			@cut.stop
			@paste.stop>
			<CodeMirrorEditor
				v-model="draft"
				:type
				:mode
				:readonly
				:show-line-numbers
				:autofocus
				@change="commit"
				@save="save" />
		</div>
		<div v-if="actionButton" class="absolute bottom-1.5 right-1.5 flex gap-1">
			<Button
				@click="actionButton?.handler"
				variant="subtle"
				class="!h-6 !w-6 border !border-outline-gray-2 bg-surface-base [&>svg]:!h-3.5 [&>svg]:!w-3.5"
				:icon="actionButton.icon"
				:title="actionButton.label"
				:disabled="readonly"></Button>
		</div>
		<span class="mt-1 text-p-xs text-ink-gray-6" v-show="description" v-html="description"></span>
		<Button v-if="showSaveButton" variant="solid" @click="save" class="mt-3" :disabled="!isDirty || readonly">
			{{ __("Save") }}
		</Button>
	</div>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import { computed, defineAsyncComponent, ref, watch } from "vue";

// keeps the CodeMirror stack out of the main editor bundle
const CodeMirrorEditor = defineAsyncComponent(() => import("./CodeMirror/CodeMirrorEditor.vue"));

const props = withDefaults(
	defineProps<{
		modelValue?: Object | String | Array<any>;
		type?: "JSON" | "HTML" | "Python" | "JavaScript" | "CSS";
		mode?: "block" | "page" | "component";
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
		autofocus: false,
		showSaveButton: false,
		description: "",
	},
);

const emit = defineEmits(["save", "update:modelValue"]);

const modelText = computed(() => {
	const value = props.modelValue ?? "";
	if (props.type !== "JSON" && typeof value !== "object") return value as string;
	try {
		return JSON.stringify(value, null, 2);
	} catch {
		return String(value);
	}
});

const draft = ref(modelText.value);
const isDirty = computed(() => draft.value !== modelText.value);

watch(modelText, (text) => (draft.value = text));

function parse(text: string) {
	return props.type === "JSON" && text ? JSON.parse(text) : text;
}

function commit() {
	if (props.showSaveButton || props.readonly || !isDirty.value) return;
	try {
		emit("update:modelValue", parse(draft.value));
	} catch {
		// invalid JSON stays in the editor until it parses
	}
}

function save() {
	if (props.readonly) return;
	emit(props.showSaveButton ? "save" : "update:modelValue", parse(draft.value));
}

defineExpose({ isDirty });
</script>
