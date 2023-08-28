<template>
	<component :is="block.getTag()" ref="component" @click.stop @dblclick.stop :key="editor">
		<div v-html="textContent" v-show="!editor" @click="handleClick"></div>
		<editor-content @click="handleClick" :editor="editor" v-if="editor" />
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
import { Editor, EditorContent } from "@tiptap/vue-3";
import { Ref, computed, onBeforeMount, onBeforeUnmount, ref, watch } from "vue";

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
		if (props.block.getDataKey("property") === "innerHTML" && props.data[props.block.getDataKey("key")]) {
			innerHTML = props.data[props.block.getDataKey("key")];
		}
	}
	return innerHTML;
});

let editor: Ref<Editor | null> = ref(null);

const isEditable = computed(() => {
	return store.builderState.editableBlock === props.block;
});

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
			store.history.pause();
			editor.value?.commands.focus("all");
		} else {
			store.history.resume();
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

if (!props.preview) {
	watch(
		() => props.block.isSelected(),
		() => {
			// only load editor if block is selected for performance reasons
			if (props.block.isSelected()) {
				editor.value = new Editor({
					content: textContent.value,
					extensions: [StarterKit, TextStyle, Color, FontFamily],
					onUpdate({ editor }) {
						if (props.block.getInnerHTML() === editor.getHTML()) {
							return;
						}
						props.block.setInnerHTML(editor.getHTML());
					},
					autofocus: false,
					injectCSS: false,
				});
				props.block.getEditor = () => editor.value || null;
				editor.value?.setEditable(isEditable.value);
			} else {
				editor.value?.destroy();
				editor.value = null;
			}
		}
	);

	onBeforeUnmount(() => {
		editor.value?.destroy();
	});
}

onBeforeMount(() => {
	let html = props.block.getInnerHTML() || "";
	setFontFromHTML(html);
});

defineExpose({
	component,
});
</script>
