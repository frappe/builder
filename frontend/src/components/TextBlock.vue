<template>
	<component :is="block.getTag()" ref="component" @click.stop @dblclick.stop>
		<editor-content @click="handleClick" :editor="editor" />
	</component>
</template>

<script setup lang="ts">
import Block from "@/utils/block";
import { Color } from "@tiptap/extension-color";
import { FontFamily } from "@tiptap/extension-font-family";
import TextStyle from "@tiptap/extension-text-style";
import StarterKit from "@tiptap/starter-kit";
import { EditorContent, useEditor } from "@tiptap/vue-3";
import { Ref, computed, onBeforeMount, onBeforeUnmount, ref, watch } from "vue";

import useStore from "@/store";
import { setFontFromHTML } from "@/utils/fontManager";
const store = useStore();

const props = defineProps({
	block: {
		type: Block,
		required: true,
	},
});

const component = ref(null) as Ref<HTMLElement | null>;

const textContent = computed(() => {
	return props.block.innerHTML;
});
const editor = useEditor({
	content: textContent.value,
	extensions: [StarterKit, TextStyle, Color, FontFamily],
	onUpdate({ editor }) {
		props.block.innerHTML = editor.getHTML();
	},
	autofocus: false,
	injectCSS: false,
});

onBeforeMount(() => {
	let html = props.block.innerHTML || "";
	setFontFromHTML(html);
});

onBeforeUnmount(() => {
	editor.value?.destroy();
});

props.block.getEditor = () => editor.value || null;

const isEditable = computed(() => {
	return props.block === store.builderState.editableBlock;
});

watch(isEditable, (newValue) => {
	editor.value?.setEditable(isEditable.value);
	if (newValue) {
		editor.value?.commands.focus("all");
	}
});

const handleClick = (e: MouseEvent) => {
	if (isEditable.value) {
		e.stopPropagation();
	}
};

watch(
	() => textContent.value,
	(newValue, oldValue) => {
		const isSame = newValue === editor.value?.getHTML();
		if (isSame) {
			return;
		}
		editor.value?.commands.setContent(newValue || "", false, {
			preserveWhitespace: "full",
		});
	}
);

defineExpose({
	component,
});
</script>
