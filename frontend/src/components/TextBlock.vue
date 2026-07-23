<template>
	<component :is="block.getTag()" ref="component" :key="editor" class="__text_block__">
		<div
			class="__text_content__ bg-clip-[inherit] bg-inherit [-webkit-background-clip:inherit] [background-image:inherit]"
			v-html="textContent"
			v-show="!editor && textContent"
			@click="handleClick"></div>
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
			class="__text_editor__ bg-clip-[inherit] relative bg-inherit [-webkit-background-clip:inherit] [background-image:inherit]"
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
import { BlockValueResolver } from "@/utils/blockValueResolver";
import { setFontFromHTML } from "@/utils/fontManager";
import type { PauseId } from "@/utils/useCanvasHistory";
import { Color } from "@tiptap/extension-color";
import { FontFamily } from "@tiptap/extension-font-family";
import { TextStyle } from "@tiptap/extension-text-style";
import { Underline } from "@tiptap/extension-underline";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { StarterKit } from "@tiptap/starter-kit";
import { Editor, EditorContent, Extension } from "@tiptap/vue-3";
import { vOnClickOutside } from "@vueuse/components";
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
		componentData?: Record<string, any> | null;
		defaultProps?: Record<string, any> | null;
		breakpoint?: string;
	}>(),
	{
		preview: false,
		data: () => ({}),
		componentData: null,
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

const valueResolver = new BlockValueResolver({
	block: () => props.block,
	data: () => props.data ?? null,
	componentData: () => props.componentData ?? null,
	defaultProps: () => props.defaultProps ?? null,
});

const textContent = computed(() => {
	let innerHTML = props.block.getInnerHTML();
	const dynamicContent = getDynamicContent();
	if (dynamicContent) {
		innerHTML = dynamicContent;
	}
	return String(innerHTML ?? "");
});

const getDynamicContent = () => {
	return valueResolver.applyDynamicValues("key", { innerHTML: null }).innerHTML;
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
		if (!editor.value) return;

		const innerHTML = getInnerHTML(editor.value);
		if (newValue === innerHTML) return;

		// If plain text is entered but current content has HTML styling, preserve it
		const isPlainText = !/<[^>]+>/.test(newValue);
		const hasStyles = /<[^>]+style=/.test(innerHTML) || /<(em|strong|i|b|u)/.test(innerHTML);

		if (isPlainText && hasStyles && newValue.trim()) {
			const tempDiv = document.createElement("div");
			tempDiv.innerHTML = innerHTML;

			if (tempDiv.textContent !== newValue) {
				// Update only the text content, preserving all HTML tags
				const walker = document.createTreeWalker(tempDiv, NodeFilter.SHOW_TEXT);
				const textNode = walker.nextNode();
				if (textNode) {
					textNode.textContent = newValue;
					editor.value.commands.setContent(tempDiv.innerHTML, { emitUpdate: false });
					return;
				}
			}
			return;
		}

		editor.value.commands.setContent(newValue || "", { emitUpdate: false });
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
	// a lone attribute-less <p> wrapper is redundant inside the block's own tag
	// (and a block box inside inline elements like span/a breaks their layout)
	const doc = editor.state.doc;
	const wrapped = innerHTML.match(/^<p>([\s\S]*)<\/p>$/);
	if (doc.childCount === 1 && doc.firstChild?.type.name === "paragraph" && wrapped) {
		innerHTML = wrapped[1];
	}
	return innerHTML;
};

const destroyEditor = () => {
	if (!editor.value) return;
	// the editor stash lives on the shared Block prototype; only clear it
	// when it still points at this component's editor
	if (props.block.getEditor() === editor.value) {
		// @ts-ignore
		props.block.__proto__.editor = null;
	}
	editor.value.destroy();
	editor.value = null;
};

if (!props.preview) {
	watch(
		() => [
			canvasStore.activeCanvas?.isSelected(props.block),
			props.breakpoint,
			canvasStore.activeCanvas?.activeBreakpoint,
		],
		() => {
			if (
				canvasStore.activeCanvas?.isSelected(props.block) &&
				canvasStore.activeCanvas?.activeBreakpoint === props.breakpoint &&
				!blockController.multipleBlocksSelected()
			) {
				// undo/redo swaps the Block under a reused component, so a live
				// editor may still exist here; destroy it or it leaks
				destroyEditor();
				editor.value = new Editor({
					content: textContent.value,
					extensions: [
						StarterKit.configure({
							link: { openOnClick: false },
							underline: false,
							// Disable the auto-appended trailing paragraph. StarterKit's TrailingNode
							// extension re-adds an empty <p> after any non-paragraph block (lists,
							// headings, etc.), which makes the trailing empty line undeletable and
							// leaks into the saved/rendered innerHTML as a blank line.
							trailingNode: false,
						}),
						TextStyle.extend({
							addGlobalAttributes() {
								return [
									{
										types: ["textStyle"],
										attributes: {
											style: {
												parseHTML: (element) => element.getAttribute("style"),
												renderHTML: (attributes) => (attributes.style ? { style: attributes.style } : {}),
											},
										},
									},
								];
							},
						}),
						Color.configure({
							types: ["textStyle"],
						}),
						FontFamily,
						FontFamilyPasteRule,
						Underline,
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
				destroyEditor();
			}
		},
		{ immediate: true },
	);

	onBeforeUnmount(destroyEditor);
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
/* no box — a block box inside inline tags (span/a) fragments their background/radius */
.__text_content__ {
	display: contents;
}

/* the contenteditable editor root needs a box, so keep it inline-level inside inline tags */
:is(span, a, b, i, em, strong, cite, label).__text_block__ > .__text_editor__ {
	display: inline-block;
}
:is(span, a, b, i, em, strong, cite, label).__text_block__ :deep(.ProseMirror p) {
	display: inline;
}

.__text_block__ :deep([contenteditable="true"]) {
	caret-color: currentcolor;
	/* blocks inherit `select-none`; re-enable native text selection while editing */
	user-select: text;
	-webkit-user-select: text;
}

.__text_block__ :deep([contenteditable="true"]):focus-visible {
	outline: none;
}

.__text_block__ :deep(.ProseMirror) {
	white-space: pre-wrap;
	word-break: unset;
}

.__text_block__ :deep(br + .ProseMirror-trailingBreak) {
	display: none;
}
</style>
