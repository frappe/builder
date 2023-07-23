<template>
	<component :is="block.getTag()" ref="component">
		<editor-content @click="handleClick" :editor="editor" />
	</component>
</template>

<script setup lang="ts">
import Block from "@/utils/block";
import { Color } from "@tiptap/extension-color";
import TextStyle from "@tiptap/extension-text-style";
import StarterKit from "@tiptap/starter-kit";
import { EditorContent, useEditor } from "@tiptap/vue-3";
import { Ref, computed, onMounted, onUnmounted, ref, watch, watchEffect } from "vue";

import useStore from "@/store";
const store = useStore();

const props = defineProps({
	block: {
		type: Block,
		required: true,
	},
	modelValue: {
		type: String,
		default: "",
	},
});

const emit = defineEmits(["update:modelValue"]);

const component = ref(null) as Ref<HTMLElement | null>;
const editor = useEditor({
	content: props.modelValue,
	extensions: [StarterKit, TextStyle, Color],
	onUpdate({ editor }) {
		emit("update:modelValue", editor.getHTML());
	},
	autofocus: false,
	injectCSS: false,
});

onMounted(() => {
	editor.value?.commands.resetAttributes("paragraph", ["style", "class"]);
});

onUnmounted(() => {
	editor.value?.destroy();
});

props.block.getEditor = () => editor.value;

const isEditable = computed(() => {
	return props.block === store.builderState.editableBlock;
});

watchEffect(() => {
	editor.value?.setEditable(isEditable.value);
});

const handleClick = (e: MouseEvent) => {
	if (isEditable.value) {
		e.stopPropagation();
	}
};

watch(
	() => props.modelValue,
	(newValue, oldValue) => {
		console.log(newValue, oldValue);
		const isSame = newValue === oldValue;
		if (isSame) {
			console.log("same");
			return;
		}
		editor.value?.commands.setContent(newValue, false, {
			preserveWhitespace: "full",
		});
	}
);

defineExpose({
	component,
});
</script>
