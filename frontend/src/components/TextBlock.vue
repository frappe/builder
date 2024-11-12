<template>
	<component
		:is="block.getTag()"
		ref="component"
		@click.stop
		@dblclick.stop
		:key="editor"
		class="__text_block__">
		<div v-html="textContent" v-show="!editor && textContent" @click="handleClick"></div>
		<bubble-menu
			ref="menu"
			:editor="editor"
			:tippy-options="{
				appendTo: overlayElement,
				onCreate: (instance) => {
					watch(
						() => canvasProps,
						() => {
							if (canvasProps?.panning || canvasProps?.scaling) {
								instance.hide();
							} else {
								instance.show();
							}
						},
						{ deep: true },
					);
				},
			}"
			v-if="editor"
			class="z-50 rounded-md border border-outline-gray-3 bg-surface-white p-1 text-lg text-text-icons-gray-9 shadow-2xl">
			<div v-if="settingLink" class="flex">
				<TextInput
					v-model="textLink"
					placeholder="https://example.com"
					class="link-input w-56 text-sm [&>input]:border-outline-gray-1 [&>input]:bg-surface-gray-2 [&>input]:text-text-icons-gray-8 [&>input]:hover:!border-outline-gray-2 [&>input]:hover:!bg-surface-gray-1 focus:[&>input]:border-outline-gray-3 focus:[&>input]:bg-surface-gray-1 focus:[&>input]:ring-outline-gray-3 [&>input]:focus-visible:bg-surface-gray-1"
					@keydown.enter="
						() => {
							if (!linkInput) return;
							setLink(linkInput.el.value);
						}
					"
					ref="linkInput" />
				<BuilderButton @click="() => setLink(linkInput?.el.value)" class="ml-1" variant="outline">
					<FeatherIcon class="h-3 w-3" name="check" />
				</BuilderButton>
				<BuilderButton
					@click="
						() => {
							textLink = '';
							setLink(null);
						}
					"
					class="ml-1">
					<FeatherIcon class="h-3 w-3" name="x" />
				</BuilderButton>
			</div>
			<div v-show="!settingLink" class="flex gap-1">
				<button
					@click="setHeading(1)"
					class="rounded px-2 py-1 text-sm hover:bg-surface-gray-2"
					:class="{ 'bg-surface-gray-3': block.getElement() === 'h1' }">
					<code>H1</code>
				</button>
				<button
					@click="setHeading(2)"
					class="rounded px-2 py-1 text-sm hover:bg-surface-gray-2"
					:class="{ 'bg-surface-gray-3': block.getElement() === 'h2' }">
					<code>H2</code>
				</button>
				<button
					@click="setHeading(3)"
					class="rounded px-2 py-1 text-sm hover:bg-surface-gray-2"
					:class="{ 'bg-surface-gray-3': block.getElement() === 'h3' }">
					<code>H3</code>
				</button>
				<button
					v-show="!block.isHeader()"
					@click="editor?.chain().focus().toggleBold().run()"
					class="rounded px-2 py-1 hover:bg-surface-gray-2"
					:class="{ 'bg-surface-gray-3': editor.isActive('bold') }">
					<FeatherIcon class="h-3 w-3" name="bold" />
				</button>
				<button
					v-show="!block.isHeader()"
					@click="editor?.chain().focus().toggleItalic().run()"
					class="rounded px-2 py-1 hover:bg-surface-gray-2"
					:class="{ 'bg-surface-gray-3': editor.isActive('italic') }">
					<FeatherIcon class="h-3 w-3" name="italic" />
				</button>
				<button
					v-show="!block.isHeader()"
					@click="editor?.chain().focus().toggleStrike().run()"
					class="rounded px-2 py-1 hover:bg-surface-gray-2"
					:class="{ 'bg-surface-gray-3': editor.isActive('strike') }">
					<StrikeThroughIcon />
				</button>
				<button
					v-show="!block.isHeader()"
					@click="
						() => {
							if (!editor) return;
							enableLinkInput();
						}
					"
					class="rounded px-2 py-1 hover:bg-surface-gray-2"
					:class="{ 'bg-surface-gray-3': editor.isActive('link') }">
					<FeatherIcon class="h-3 w-3" name="link" />
				</button>
			</div>
		</bubble-menu>
		<editor-content
			@click="handleClick"
			:editor="editor"
			@mousedown="selectionTriggered = true"
			@mousemove="
				() => {
					if (selectionTriggered) {
						store.preventClick = true;
					}
				}
			"
			@mouseup="selectionTriggered = false"
			v-if="editor && showEditor"
			class="relative z-50"
			:style="block.getRawStyles()"
			@keydown="handleKeydown" />
		<slot />
	</component>
</template>

<script setup lang="ts">
import useStore from "@/store";
import Block from "@/utils/block";
import blockController from "@/utils/blockController";
import { setFontFromHTML } from "@/utils/fontManager";
import { getDataForKey } from "@/utils/helpers";
import { Color } from "@tiptap/extension-color";
import { FontFamily } from "@tiptap/extension-font-family";
import { Link } from "@tiptap/extension-link";
import TextStyle from "@tiptap/extension-text-style";
import StarterKit from "@tiptap/starter-kit";
import { BubbleMenu, Editor, EditorContent, Extension } from "@tiptap/vue-3";
import { TextInput } from "frappe-ui";
import { Plugin, PluginKey } from "prosemirror-state";
import { Ref, computed, inject, nextTick, onBeforeMount, onBeforeUnmount, ref, watch } from "vue";
import StrikeThroughIcon from "./Icons/StrikeThrough.vue";

const store = useStore();
const dataChanged = ref(false);
const settingLink = ref(false);
const textLink = ref("");
const linkInput = ref(null) as Ref<typeof TextInput | null>;
const component = ref(null) as Ref<HTMLElement | null>;
const overlayElement = document.querySelector("#overlay") as HTMLElement;
let editor: Ref<Editor | null> = ref(null);
let selectionTriggered = false as boolean;

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

const textContent = computed(() => {
	let innerHTML = props.block.getInnerHTML();
	if (props.data) {
		if (props.block.getDataKey("property") === "innerHTML") {
			innerHTML = getDataForKey(props.data, props.block.getDataKey("key")) || innerHTML;
		}
	}
	return String(innerHTML ?? "");
});

const isEditable = computed(() => {
	return store.editableBlock === props.block;
});

const showEditor = computed(() => {
	return !((props.block.isLink() || props.block.isButton()) && props.block.hasChildren());
});

onBeforeMount(() => {
	let html = props.block.getInnerHTML() || "";
	setFontFromHTML(html);
});

watch(
	() => isEditable.value,
	(editable) => {
		editor.value?.setEditable(editable);
		if (editable) {
			store.activeCanvas?.history.pause();
			editor.value?.commands.focus("all");
		} else {
			store.activeCanvas?.history.resume(dataChanged.value);
			dataChanged.value = false;
		}
	},
	{ immediate: true },
);

watch(
	() => textContent.value,
	(newValue) => {
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
		() => store.activeCanvas?.isSelected(props.block),
		() => {
			// only load editor if block is selected for performance reasons
			if (store.activeCanvas?.isSelected(props.block) && !blockController.multipleBlocksSelected()) {
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
						FontFamilyPasteRule,
					],
					enablePasteRules: false,
					onUpdate({ editor }) {
						let innerHTML = getInnerHTML(editor as Editor);
						if (props.block.getInnerHTML() === innerHTML) {
							return;
						}
						dataChanged.value = true;
						props.block.setInnerHTML(innerHTML);
					},
					onSelectionUpdate: ({ editor }) => {
						settingLink.value = false;
						textLink.value = "";
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

const handleKeydown = (e: KeyboardEvent) => {
	if (e.key === "k" && e.metaKey) {
		enableLinkInput();
	}
};

const enableLinkInput = () => {
	settingLink.value = true;
	// check if link is already set on selection
	const link = editor.value?.isActive("link") ? editor.value?.getAttributes("link").href : null;
	textLink.value = link || "";
	nextTick(() => {
		if (linkInput.value) {
			const input = document.querySelector(".link-input") as HTMLInputElement;
			input.focus();
		}
	});
};

const setLink = (value: string | null) => {
	if (!value && !textLink.value) {
		editor.value?.chain().focus().unsetLink().run();
	} else {
		editor.value
			?.chain()
			.focus()
			.setLink({ href: value || textLink.value })
			.run();
		textLink.value = "";
	}
	settingLink.value = false;
};

const setHeading = (level: 1 | 2 | 3) => {
	props.block.setBaseStyle("font-size", level === 1 ? "2rem" : level === 2 ? "1.5rem" : "1.25rem");
	props.block.setBaseStyle("font-weight", "bold");
	const tag = `h${level}`;
	if (props.block.element === tag) {
		props.block.element = "p";
	} else {
		props.block.element = tag;
	}

	nextTick(() => {
		props.block.selectBlock();
	});
};

const handleClick = (e: MouseEvent) => {
	if (isEditable.value) {
		e.stopPropagation();
	}
};

defineExpose({
	component,
});
</script>
<style>
.__text_block__ [contenteditable="true"] {
	caret-color: currentcolor !important;
}
</style>
