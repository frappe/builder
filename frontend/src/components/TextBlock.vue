<template>
	<component :is="block.getTag()" ref="component" :key="editor" class="__text_block__">
		<div v-html="textContent" v-show="!editor && textContent" @click="handleClick"></div>
		<bubble-menu
			ref="menu"
			:editor="editor"
			:tippy-options="{
				appendTo: overlayElement,
				interactive: true,
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
			class="z-50 rounded-md border border-outline-gray-3 bg-surface-white p-1 text-lg text-ink-gray-9 shadow-2xl"
			:should-show="() => isEditable">
			<div
				v-if="settingLink"
				class="flex flex-col gap-2 p-1"
				v-on-click-outside="
					() => {
						nextTick(() => {
							setLink(null, false);
						});
					}
				">
				<div class="flex">
					<Input
						type="text"
						v-model="textLink"
						placeholder="https://example.com"
						class="link-input !w-56 text-sm"
						@keydown.enter="
							() => {
								if (!linkInput) return;
								const input = linkInput.$el.querySelector('input') as HTMLInputElement;
								setLink(input.value);
							}
						"
						ref="linkInput" />
				</div>
				<Input
					type="checkbox"
					:label="'Open in New Tab'"
					class="text-xs"
					v-model="openInNewTab"
					@change="() => setLink(textLink, false)"></Input>
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
					<FeatherIcon class="h-3 w-3" name="bold" :stroke-width="2" />
				</button>
				<button
					v-show="!block.isHeader()"
					@click="editor?.chain().focus().toggleItalic().run()"
					class="rounded px-2 py-1 hover:bg-surface-gray-2"
					:class="{ 'bg-surface-gray-3': editor.isActive('italic') }">
					<FeatherIcon class="h-3 w-3" name="italic" :stroke-width="2" />
				</button>
				<button
					v-show="!block.isHeader()"
					@click="editor?.chain().focus().toggleStrike().run()"
					class="rounded px-2 py-1 hover:bg-surface-gray-2"
					:class="{ 'bg-surface-gray-3': editor.isActive('strike') }">
					<StrikeThroughIcon />
				</button>

				<button
					v-show="!block.isHeader() && !block.isLink() && !block.isButton()"
					@click="
						() => {
							if (!editor) return;
							enableLinkInput();
						}
					"
					class="rounded px-2 py-1 hover:bg-surface-gray-2"
					:class="{ 'bg-surface-gray-3': editor.isActive('link') }">
					<FeatherIcon class="h-3 w-3" name="link" :stroke-width="2" />
				</button>
				<ColorPicker
					:modelValue="selectedColor"
					@update:modelValue="setTextColor"
					:show-input="true"
					placement="top"
					:appendTo="overlayElement"
					v-show="!block.isHeader()"
					popoverClass="!min-w-fit">
					<template #target="{ togglePopover, isOpen }">
						<button v-show="!block.isHeader()" class="rounded px-2 py-1 hover:bg-surface-gray-2">
							<div class="p-1">
								<div
									class="h-4 w-4 rounded shadow-sm"
									@click="
										() => {
											togglePopover();
										}
									"
									:style="{
										background:
											editor?.isActive('textStyle') && editor?.getAttributes('textStyle').color
												? editor?.getAttributes('textStyle').color
												: `url(/assets/builder/images/color-circle.png) center / contain`,
									}"></div>
							</div>
						</button>
					</template>
					<template>
						<Input
							type="text"
							:modelValue="selectedColor"
							class="!w-32 text-sm"
							@update:modelValue="setTextColor" />
					</template>
				</ColorPicker>
			</div>
		</bubble-menu>
		<editor-content
			@click="handleClick"
			:editor="editor"
			@mousedown="selectionTriggered = true"
			@mousemove="
				() => {
					if (selectionTriggered) {
						canvasStore.preventClick = true;
					}
				}
			"
			@keydown.esc="
				() => {
					canvasStore.editableBlock = null;
				}
			"
			v-on-click-outside="
				(e) => {
					if ((e.target as HTMLElement).closest('.canvas-container')) {
						canvasStore.editableBlock = null;
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
import type Block from "@/block";
import ColorPicker from "@/components/Controls/ColorPicker.vue";
import Input from "@/components/Controls/Input.vue";
import useCanvasStore from "@/stores/canvasStore";
import blockController from "@/utils/blockController";
import { setFontFromHTML } from "@/utils/fontManager";
import { getDataForKey } from "@/utils/helpers";
import { Color } from "@tiptap/extension-color";
import { FontFamily } from "@tiptap/extension-font-family";
import { Link } from "@tiptap/extension-link";
import TextStyle from "@tiptap/extension-text-style";
import Underline from "@tiptap/extension-underline";
import StarterKit from "@tiptap/starter-kit";
import { BubbleMenu, Editor, EditorContent, Extension } from "@tiptap/vue-3";
import { vOnClickOutside } from "@vueuse/components";
import { debounce } from "frappe-ui";
import { Plugin, PluginKey } from "prosemirror-state";
import { Ref, computed, inject, nextTick, onBeforeMount, onBeforeUnmount, ref, watch } from "vue";
import { toast } from "vue-sonner";
import StrikeThroughIcon from "./Icons/StrikeThrough.vue";

const canvasStore = useCanvasStore();

const dataChanged = ref(false);
const settingLink = ref(false);
const textLink = ref("");
const openInNewTab = ref(false);
const linkInput = ref(null) as Ref<typeof Input | null>;
const component = ref(null) as Ref<HTMLElement | null>;
const overlayElement = document.querySelector("#overlay") as HTMLElement;
let editor: Ref<Editor | null> = ref(null);
let selectionTriggered = false as boolean;

const selectedColor = computed(() => {
	if (editor.value?.isActive("textStyle")) {
		return editor.value.getAttributes("textStyle").color || "#000000";
	}
});

const props = withDefaults(
	defineProps<{
		block: Block;
		preview?: boolean;
		data?: Record<string, any>;
		breakpoint?: string;
	}>(),
	{
		preview: false,
		data: () => ({}),
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

const textContent = computed(() => {
	let innerHTML = props.block.getInnerHTML();
	if (props.data) {
		const dynamicContent = getDynamicContent();
		if (dynamicContent) {
			innerHTML = dynamicContent;
		}
	}
	return String(innerHTML ?? "");
});

const getDynamicContent = () => {
	let innerHTML = null as string | null;
	if (props.block.getDataKey("property") === "innerHTML") {
		innerHTML = getDataForKey(props.data, props.block.getDataKey("key")) ?? innerHTML;
	}
	props.block.dynamicValues
		?.filter((dataKeyObj: BlockDataKey) => {
			return dataKeyObj.property === "innerHTML" && dataKeyObj.type === "key";
		})
		?.forEach((dataKeyObj: BlockDataKey) => {
			innerHTML = getDataForKey(props.data as Object, dataKeyObj.key as string) ?? innerHTML;
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

watch(
	() => isEditable.value,
	(editable) => {
		editor.value?.setEditable(editable);
		if (editable) {
			canvasStore.activeCanvas?.history?.pause();
			editor.value?.commands.focus("all");
		} else {
			canvasStore.activeCanvas?.history?.resume(undefined, dataChanged.value, true);
			dataChanged.value = false;
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
		const blockWarnings = {
			isHeader: "You cannot make heading a link",
			isLink: "You cannot add link inside a link block",
			isButton: "You cannot add link inside a button block",
		};

		const blockType = Object.entries(blockWarnings).find(([type]) => props.block[type]());
		if (blockType) {
			toast.warning(blockType[1]);
		} else {
			enableLinkInput();
		}
	}
};

const enableLinkInput = () => {
	settingLink.value = true;
	// check if link is already set on selection
	const link = editor.value?.isActive("link") ? editor.value?.getAttributes("link").href : null;
	textLink.value = link || "";
	openInNewTab.value = editor.value?.isActive("link")
		? editor.value?.getAttributes("link").target === "_blank"
		: false;
	nextTick(() => {
		if (linkInput.value) {
			const input = linkInput.value.$el.querySelector("input") as HTMLInputElement;
			input.focus();
		}
	});
};

const setLink = (value: string | null, closeModal = true) => {
	if (!value && !textLink.value) {
		editor.value?.chain().focus().unsetLink().run();
	} else {
		const href = value || textLink.value;
		// const isExternal = href.startsWith("http") || href.startsWith("//");
		editor.value
			?.chain()
			.focus()
			.setLink({
				href,
				target: openInNewTab.value ? "_blank" : "_self",
			})
			.run();
	}
	if (closeModal) {
		settingLink.value = false;
		textLink.value = "";
	}
};

const setHeading = (level: 1 | 2 | 3) => {
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

const isEntireTextSelected = () => {
	if (!editor.value) return false;
	const { from, to } = editor.value.state.selection;
	const textContent = editor.value.state.doc.textContent;
	const textLength = textContent.length;
	return from === 0 && to >= textLength;
};

const setTextColor = debounce((color: string | undefined) => {
	const colorValue = color as string;
	if (!colorValue) {
		editor.value?.chain().focus().setColor(colorValue).run();
		if (isEntireTextSelected()) {
			props.block.setStyle("color", "");
		}
		return;
	}

	editor.value?.chain().focus().setColor(colorValue).run();
	if (isEntireTextSelected()) {
		props.block.setStyle("color", colorValue);
	}
}, 50);

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
</style>
