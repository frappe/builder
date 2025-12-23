<template>
	<component :is="block.getTag()" ref="component" :key="editor" class="__text_block__">
		<div v-html="textContent" v-show="!editor && textContent" @click="handleClick"></div>
		<TextBlockBubbleMenu
			v-if="editor"
			:block="block"
			:editor="editor"
			:canvas-props="canvasProps"
			:overlay-element="overlayElement"
			:is-editable="isEditable"
			ref="bubbleMenu" />
		<editor-content
			@click="handleClick"
			:editor="editor"
			@mousedown="selectionTriggered = true"
			@mousemove="handleMouseMove"
			@keydown.esc="handleEscKey"
			v-on-click-outside="handleClickOutside"
			@mouseup="selectionTriggered = false"
			v-if="editor && showEditor"
			class="relative"
			:style="block.getRawStyles()"
			@keydown="(e: KeyboardEvent) => bubbleMenu?.handleKeydown(e)" />
		<slot />
	</component>
</template>

<script setup lang="ts">
import type Block from "@/block";
import TextBlockBubbleMenu from "@/components/TextBlockBubbleMenu.vue";
import useCanvasStore from "@/stores/canvasStore";
import blockController from "@/utils/blockController";
import { setFontFromHTML } from "@/utils/fontManager";
import { getDataForKey, getPropValue } from "@/utils/helpers";
import type { PauseId } from "@/utils/useCanvasHistory";
import { Color } from "@tiptap/extension-color";
import { FontFamily } from "@tiptap/extension-font-family";
import { Link } from "@tiptap/extension-link";
import TextStyle from "@tiptap/extension-text-style";
import Underline from "@tiptap/extension-underline";
import StarterKit from "@tiptap/starter-kit";
import { Editor, EditorContent, Extension } from "@tiptap/vue-3";
import { vOnClickOutside } from "@vueuse/components";
import { Plugin, PluginKey } from "prosemirror-state";
import { Ref, computed, inject, onBeforeMount, onBeforeUnmount, ref, watch } from "vue";

const canvasStore = useCanvasStore();

const dataChanged = ref(false);
const component = ref(null) as Ref<HTMLElement | null>;
const bubbleMenu = ref(null) as Ref<{ handleKeydown: (e: KeyboardEvent) => void } | null>;
const overlayElement = document.querySelector("#overlay") as HTMLElement;
let editor: Ref<Editor | null> = ref(null);
let selectionTriggered = false as boolean;

const props = withDefaults(
	defineProps<{
		block: Block;
		preview?: boolean;
		data?: Record<string, any>;
		blockData?: Record<string, any> | null;
		defaultProps?: Record<string, any> | null;
		breakpoint?: string;
	}>(),
	{
		preview: false,
		data: () => ({}),
		blockData: null,
		defaultProps: null,
		breakpoint: "desktop",
	},
);

const canvasProps = !props.preview ? (inject("canvasProps") as CanvasProps) : null;

const FontFamilyPasteRule = Extension.create({
	name: "fontFamilyPasteRule",
	addProseMirrorPlugins() {
		return [
			new Plugin({
				key: new PluginKey("fontFamilyPasteRule"),
				props: {
					transformPastedHTML(html) {
						const div = document.createElement("div");
						div.innerHTML = html;
						const removeFontFamily = (element: HTMLElement) => {
							if (element.style) {
								element.style.fontFamily = "";
							}
							for (let i = 0; i < element.children.length; i++) {
								removeFontFamily(element.children[i] as HTMLElement);
							}
						};
						removeFontFamily(div);
						return div.innerHTML;
					},
				},
			}),
		];
	},
});

const hasBlockProps = computed(() => {
	return props.defaultProps || Object.keys(props.block.getBlockProps()).length > 0;
});

const textContent = computed(() => {
	let innerHTML = props.block.getInnerHTML();
	if (props.data || hasBlockProps.value) {
		const dynamicContent = getDynamicContent();
		if (dynamicContent) {
			innerHTML = dynamicContent;
		}
	}
	return String(innerHTML ?? "");
});

const getDataScriptValue = (path: string): any => {
	return getDataForKey(props.data, path);
};
const getBlockDataScriptValue = (path: string): any => {
	return getDataForKey(props.blockData || {}, path);
};

const getDynamicContent = () => {
	let innerHTML = null as string | null;

	if (props.block.getDataKey("property") === "innerHTML") {
		let value;
		if (props.block.getDataKey("comesFrom") === "props") {
			// props are checked first as unavailablity of comesFrom means it comes from dataScript (legacy)
			value = getPropValue(
				props.block.getDataKey("key"),
				props.block,
				getDataScriptValue,
				getBlockDataScriptValue,
				props.defaultProps,
			);
		} else if (props.block.getDataKey("comesFrom") === "blockDataScript") {
			value = getBlockDataScriptValue(props.block.getDataKey("key"));
		} else {
			value = getDataScriptValue(props.block.getDataKey("key"));
		}
		innerHTML = value ?? innerHTML;
	}
	props.block.dynamicValues
		?.filter((dataKeyObj: BlockDataKey) => {
			return dataKeyObj.property === "innerHTML" && dataKeyObj.type === "key";
		})
		?.forEach((dataKeyObj: BlockDataKey) => {
			let value;
			if (dataKeyObj.comesFrom === "props") {
				value = getPropValue(
					dataKeyObj.key as string,
					props.block,
					getDataScriptValue,
					getBlockDataScriptValue,
					props.defaultProps,
				);
			} else if (dataKeyObj.comesFrom === "blockDataScript") {
				value = getBlockDataScriptValue(dataKeyObj.key as string);
			} else {
				value = getDataScriptValue(dataKeyObj.key as string);
			}
			innerHTML = value ?? innerHTML;
		});
	return innerHTML;
};

const isEditable = computed(() => {
	return (
		canvasStore.editableBlock === props.block &&
		canvasStore.activeCanvas?.activeBreakpoint === props.breakpoint
	);
});

const showEditor = computed(() => {
	return !((props.block.isLink() || props.block.isButton()) && props.block.hasChildren());
});

onBeforeMount(() => {
	let html = props.block.getInnerHTML() || "";
	setFontFromHTML(html);
});

let pauseId: PauseId | undefined = undefined;

watch(
	() => isEditable.value,
	(editable) => {
		editor.value?.setEditable(editable);
		if (editable) {
			pauseId = canvasStore.activeCanvas?.history?.pause();
			editor.value?.commands.focus("all");
		} else {
			canvasStore.activeCanvas?.history?.resume(pauseId, dataChanged.value, pauseId === undefined);
			dataChanged.value = false;
			pauseId = undefined;
		}
	},
	{ immediate: true },
);

watch(
	() => textContent.value,
	(newValue: string) => {
		const innerHTML = getInnerHTML(editor.value);
		const isSame = newValue === innerHTML;
		if (isSame) {
			return;
		}
		editor.value?.commands.setContent(newValue || "", false);
	},
);

const getInnerHTML = (editor: Editor | null) => {
	if (!editor) {
		return "";
	}
	let innerHTML = editor.isEmpty ? "" : editor.getHTML();
	if (
		props.block.isHeader() &&
		!(
			editor.isActive("heading", { level: 1 }) ||
			editor.isActive("heading", { level: 2 }) ||
			editor.isActive("heading", { level: 3 })
		)
	) {
		innerHTML = editor?.getText();
	}
	return innerHTML;
};

if (!props.preview) {
	watch(
		() => canvasStore.activeCanvas?.isSelected(props.block),
		() => {
			// only load editor if block is selected for performance reasons
			if (canvasStore.activeCanvas?.isSelected(props.block) && !blockController.multipleBlocksSelected()) {
				editor.value = new Editor({
					content: textContent.value,
					extensions: [
						StarterKit,
						TextStyle,
						Color,
						FontFamily,
						Link.configure({
							openOnClick: false,
						}),
						Underline,
						FontFamilyPasteRule,
					],
					enablePasteRules: false,
					onUpdate({ editor }) {
						let innerHTML = getInnerHTML(editor as Editor);
						if (props.block.getInnerHTML() === innerHTML) {
							return;
						}
						dataChanged.value = true;
						if (!getDynamicContent()) {
							props.block.setInnerHTML(innerHTML);
						}
					},
					autofocus: false,
					injectCSS: false,
				});

				// @ts-ignore
				props.block.__proto__.editor = editor.value;
				editor.value?.setEditable(isEditable.value);
			} else {
				editor.value?.destroy();
				editor.value = null;
				// @ts-ignore
				props.block.__proto__.editor = null;
			}
		},
		{ immediate: true },
	);

	onBeforeUnmount(() => {
		editor.value?.destroy();
	});
}

const handleClick = (e: MouseEvent) => {
	if (isEditable.value) {
		e.stopPropagation();
	}
};

const handleMouseMove = () => {
	if (selectionTriggered) {
		canvasStore.preventClick = true;
	}
};

const handleEscKey = () => {
	canvasStore.editableBlock = null;
};

const handleClickOutside = (e: MouseEvent) => {
	if ((e.target as HTMLElement).closest(".canvas-container")) {
		canvasStore.editableBlock = null;
	}
};

defineExpose({
	component,
});
</script>
<style scoped>
.__text_block__ :deep([contenteditable="true"]) {
	caret-color: currentcolor;
}

.__text_block__ :deep(.ProseMirror) {
	word-break: unset;
}

.__text_block__ :deep(br + .ProseMirror-trailingBreak) {
	display: none;
}
</style>
