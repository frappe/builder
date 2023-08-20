<template>
	<component :is="block.getTag()" ref="component" @click.stop @dblclick.stop>
		<editor-content @click="handleClick" :editor="editor" />
		<slot />
	</component>
</template>

<script setup lang="ts">
import useStore from "@/store";
import Block from "@/utils/block";
import { setFontFromHTML } from "@/utils/fontManager";
import { Color } from "@tiptap/extension-color";
import { FontFamily } from "@tiptap/extension-font-family";
import TextStyle from "@tiptap/extension-text-style";
import StarterKit from "@tiptap/starter-kit";
import { EditorContent, useEditor } from "@tiptap/vue-3";
import { Ref, computed, onBeforeMount, onBeforeUnmount, onMounted, ref, watch } from "vue";

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

const store = useStore();
const component = ref(null) as Ref<HTMLElement | null>;

const textContent = computed(() => {
	let innerHTML = props.block.getInnerHTML();
	if (props.data) {
		if (props.block.dataKey?.property === "innerHTML" && props.data[props.block.dataKey?.key as string]) {
			innerHTML = props.data[props.block.dataKey?.key as string];
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

const isEditable = computed(() => {
	return !props.preview && store.builderState.editableBlock === props.block;
});

props.block.getEditor = () => editor.value || null;

const handleClick = (e: MouseEvent) => {
	if (isEditable.value) {
		e.stopPropagation();
	}
};

watch(
	() => isEditable.value,
	(editable) => {
		editor.value?.setEditable(editable);
		if (editable) {
			editor.value?.commands.focus("all");
		}
	}
);

watch(
	() => textContent.value,
	(newValue, oldValue) => {
		const isSame = newValue === editor.value?.getHTML();
		if (isSame) {
			return;
		}
		editor.value?.commands.setContent(newValue || "", false);
	}
);

onBeforeMount(() => {
	let html = props.block.getInnerHTML() || "";
	setFontFromHTML(html);
});

onMounted(() => {
	editor.value?.setEditable(isEditable.value);
});

onBeforeUnmount(() => {
	editor.value?.destroy();
});

defineExpose({
	component,
});
</script>
