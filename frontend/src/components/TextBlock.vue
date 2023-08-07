<template>
	<component :is="block.getTag()" ref="component" @click.stop @dblclick.stop>
		<editor-content @click="handleClick" :editor="editor" />
		<slot />
	</component>
</template>

<script setup lang="ts">
import Block from "@/utils/block";
import { Color } from "@tiptap/extension-color";
import { FontFamily } from "@tiptap/extension-font-family";
import TextStyle from "@tiptap/extension-text-style";
import StarterKit from "@tiptap/starter-kit";
import { EditorContent, useEditor } from "@tiptap/vue-3";
import { Ref, computed, onBeforeMount, onBeforeUnmount, onMounted, ref, watch } from "vue";

import useStore from "@/store";
import { setFontFromHTML } from "@/utils/fontManager";
const store = useStore();

const props = defineProps({
	block: {
		type: Block,
		required: true,
	},
	preview: {
		type: Boolean,
		default: false,
	},
	data: {
		type: Object,
		default: () => ({}),
	},
});

const component = ref(null) as Ref<HTMLElement | null>;

const textContent = computed(() => {
	let innerHTML = props.block.getInnerHTML();
	if (props.data) {
		if (props.block.dataKey?.property === "innerHTML" && props.data[props.block.dataKey?.key]) {
			innerHTML = props.data[props.block.dataKey?.key];
		}
	}
	return innerHTML;
});
const editor = useEditor({
	content: textContent.value,
	extensions: [StarterKit, TextStyle, Color, FontFamily],
	onUpdate({ editor }) {
		props.block.setInnerHTML(editor.getHTML());
	},
	autofocus: false,
	injectCSS: false,
});

onBeforeMount(() => {
	let html = props.block.getInnerHTML() || "";
	setFontFromHTML(html);

	if (!props.block.classes.includes("TextBlock")) {
		props.block.classes.push("TextBlock");
	}
});

onMounted(() => {
	editor.value?.setEditable(isEditable.value);
});

onBeforeUnmount(() => {
	editor.value?.destroy();
});

props.block.getEditor = () => editor.value || null;

const isEditable = computed(() => {
	return !props.preview && store.builderState.editableBlock === props.block;
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
