<template>
	<bubble-menu
		:editor="editor"
		:append-to="overlayElement"
		:options="{ strategy: 'absolute', placement: 'bottom' }"
		:get-referenced-virtual-element="getReferencedVirtualElement"
		:plugin-key="bubbleMenuPluginKey"
		:should-show="shouldShow"
		v-show="!canvasProps?.panning && !canvasProps?.scaling"
		v-if="editor"
		class="rounded-md border border-outline-gray-3 bg-surface-base p-1 text-lg text-ink-gray-9 shadow-2xl"
		:class="{ '!border-none !bg-transparent !p-0 !shadow-none': settingColor }">
		<div
			class="text-block-bubble-menu flex items-center justify-center"
			@mouseenter="isHoveringMenu = true"
			@mouseleave="isHoveringMenu = false"
			@mousedown="handleMenuMouseDown">
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
				<div v-show="!settingColor" class="flex gap-1">
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
						<span class="lucide-bold h-3 w-3" aria-hidden="true" />
					</button>
					<button
						v-show="!block.isHeader()"
						@click="editor?.chain().focus().toggleItalic().run()"
						class="rounded px-2 py-1 hover:bg-surface-gray-2"
						:class="{ 'bg-surface-gray-3': editor.isActive('italic') }">
						<span class="lucide-italic h-3 w-3" aria-hidden="true" />
					</button>
					<button
						v-show="!block.isHeader()"
						@click="editor?.chain().focus().toggleStrike().run()"
						class="rounded px-2 py-1 hover:bg-surface-gray-2"
						:class="{ 'bg-surface-gray-3': editor.isActive('strike') }">
						<span class="lucide-strikethrough size-4" />
					</button>

					<button
						v-show="!block.isHeader()"
						@click="editor?.chain().focus().toggleUnderline().run()"
						class="rounded px-2 py-1 hover:bg-surface-gray-2"
						:class="{ 'bg-surface-gray-3': editor.isActive('underline') }">
						<span class="lucide-underline size-4" />
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
						<span class="lucide-link h-3 w-3" aria-hidden="true" />
					</button>
				</div>
				<div v-show="!block.isHeader()">
					<ColorPicker
						ref="colorPickerRef"
						:modelValue="selectedColor"
						:show-input="true"
						placement="top"
						:portal-to="false"
						@mousedown.stop
						@update:modelValue="setTextColor"
						@open="settingColor = true"
						@close="settingColor = false">
						<template #target="{ togglePopover }">
							<button
								class="rounded px-2 py-1 hover:bg-surface-gray-2 transition-all duration-100 overflow-hidden"
								:class="settingColor ? 'h-0 p-0 m-0 opacity-0' : ''"
								@click="togglePopover()"
								@mousedown.prevent>
								<div
									class="h-5 w-5 rounded-full shadow-sm border border-outline-gray-2"
									:style="{
										background:
											editor?.isActive('textStyle') && editor?.getAttributes('textStyle').color
												? editor?.getAttributes('textStyle').color
												: `url(/assets/builder/images/color-circle.png) center / contain`,
									}"></div>
							</button>
						</template>
					</ColorPicker>
				</div>
			</div>
		</div>
	</bubble-menu>
</template>

<script setup lang="ts">
import type Block from "@/block";
import ColorPicker from "@/components/Controls/ColorPicker.vue";
import Input from "@/components/Controls/Input.vue";
import { posToDOMRect } from "@tiptap/core";
import type { Editor } from "@tiptap/vue-3";
import { BubbleMenu } from "@tiptap/vue-3/menus";
import { vOnClickOutside } from "@vueuse/components";
import { debouncedWatch } from "@vueuse/core";
import { debounce, toast } from "frappe-ui";
import { computed, nextTick, ref, watch, onBeforeUnmount, type Ref } from "vue";

const props = defineProps<{
	block: Block;
	editor: Editor;
	canvasProps: any;
	overlayElement: HTMLElement;
	isEditable: boolean;
}>();

const settingLink = ref(false);
const textLink = ref("");
const openInNewTab = ref(false);
const linkInput = ref(null) as Ref<typeof Input | null>;
const settingColor = ref(false);
const colorPickerRef = ref<any>(null);
const isHoveringMenu = ref(false);
const isMouseDownInMenu = ref(false);

const handleMouseUp = () => {
	isMouseDownInMenu.value = false;
};

const isInteractingWithMenu = () => {
	const activeEl = document.activeElement;
	const menuEl = document.querySelector(".text-block-bubble-menu");
	return !!(menuEl && activeEl && menuEl.contains(activeEl));
};

const shouldShow = (bubbleMenuProps: any) => {
	const { editor, from, to } = bubbleMenuProps;
	if (!editor) return false;
	const hasSelection = from !== to;
	if (!hasSelection) return false;

	return editor.isFocused || isHoveringMenu.value || isMouseDownInMenu.value || isInteractingWithMenu() || settingColor.value;
};

const handleMenuMouseDown = (e: MouseEvent) => {
	isMouseDownInMenu.value = true;
	const target = e.target as HTMLElement;
	if (target.tagName !== "INPUT" && !target.closest("input")) {
		e.preventDefault();
	}
};

const handleOutsideClick = (e: MouseEvent) => {
	const menuEl = document.querySelector(".text-block-bubble-menu");
	if (menuEl && !menuEl.contains(e.target as Node)) {
		colorPickerRef.value?.togglePopover(false);
		settingColor.value = false;
	}
};

let lockedRelativeRect: { left: number; top: number; width: number; height: number } | null = null;

const getSelectionRect = () => {
	if (!props.editor) return new DOMRect();
	const { view, state } = props.editor;
	const { from, to } = state.selection;
	
	try {
		return posToDOMRect(view, from, to);
	} catch (e) {
		return new DOMRect();
	}
};

const getReferencedVirtualElement = () => {
	return {
		getBoundingClientRect: () => {
			if (settingColor.value && lockedRelativeRect) {
				const editorEl = props.editor?.view.dom;
				if (editorEl) {
					const editorRect = editorEl.getBoundingClientRect();
					return new DOMRect(
						editorRect.left + lockedRelativeRect.left,
						editorRect.top + lockedRelativeRect.top,
						lockedRelativeRect.width,
						lockedRelativeRect.height
					);
				}
			}
			return getSelectionRect();
		},
		getClientRects: () => {
			if (settingColor.value && lockedRelativeRect) {
				const editorEl = props.editor?.view.dom;
				if (editorEl) {
					const editorRect = editorEl.getBoundingClientRect();
					const rect = new DOMRect(
						editorRect.left + lockedRelativeRect.left,
						editorRect.top + lockedRelativeRect.top,
						lockedRelativeRect.width,
						lockedRelativeRect.height
					);
					return [rect];
				}
			}
			const rect = getSelectionRect();
			return [rect];
		},
		contextElement: props.editor?.view.dom
	};
};

watch(settingColor, (isOpen) => {
	if (isOpen) {
		const editorEl = props.editor?.view.dom;
		if (editorEl) {
			const selectionRect = getSelectionRect();
			const editorRect = editorEl.getBoundingClientRect();
			lockedRelativeRect = {
				left: selectionRect.left - editorRect.left,
				top: selectionRect.top - editorRect.top,
				width: selectionRect.width,
				height: selectionRect.height
			};
		}
		document.addEventListener("mousedown", handleOutsideClick, true);
		window.addEventListener("mouseup", handleMouseUp);
	} else {
		lockedRelativeRect = null;
		document.removeEventListener("mousedown", handleOutsideClick, true);
		window.removeEventListener("mouseup", handleMouseUp);
		isMouseDownInMenu.value = false;
	}
	nextTick(() => {
		props.editor?.view.dispatch(
			props.editor.state.tr.setMeta(bubbleMenuPluginKey, "updatePosition")
		);
	});
});

watch(settingLink, () => {
	nextTick(() => {
		props.editor?.view.dispatch(
			props.editor.state.tr.setMeta(bubbleMenuPluginKey, "updatePosition")
		);
	});
});

onBeforeUnmount(() => {
	lockedRelativeRect = null;
	document.removeEventListener("mousedown", handleOutsideClick, true);
	window.removeEventListener("mouseup", handleMouseUp);
});

const editorRef = computed(() => props.editor);
const bubbleMenuPluginKey = "bubbleMenu";

const selectedColor = computed(() => {
	if (props.editor?.isActive("textStyle")) {
		return props.editor.getAttributes("textStyle").color || null;
	}
	return null;
});

const enableLinkInput = () => {
	settingLink.value = true;
	// check if link is already set on selection
	const link = props.editor?.isActive("link") ? props.editor?.getAttributes("link").href : null;
	textLink.value = link || "";
	openInNewTab.value = props.editor?.isActive("link")
		? props.editor?.getAttributes("link").target === "_blank"
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
		props.editor?.chain().focus().unsetLink().run();
	} else {
		const href = value || textLink.value;
		props.editor
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

// Text color functionality
const isEntireTextSelected = () => {
	if (!props.editor) return false;
	const { from, to } = props.editor.state.selection;
	const textContent = props.editor.state.doc.textContent;
	const textLength = textContent.length;
	return from === 0 && to >= textLength;
};

const setTextColor = debounce((color: string | undefined) => {
	const colorValue = color as string;
	if (!colorValue) {
		props.editor?.chain().focus().setColor(colorValue).run();
		if (isEntireTextSelected()) {
			props.block.setStyle("color", "");
		}
		return;
	}

	props.editor?.chain().focus().setColor(colorValue).run();
	if (isEntireTextSelected()) {
		props.block.setStyle("color", colorValue);
	}
}, 50);

// Keyboard handling
const handleKeydown = (e: KeyboardEvent) => {
	if (e.key === "k" && e.metaKey) {
		e.preventDefault();
		e.stopPropagation();
		const blockWarnings = {
			isHeader: "You cannot make heading a link",
			isLink: "You cannot add link inside a link block",
			isButton: "You cannot add link inside a button block",
		};

		const blockType = Object.entries(blockWarnings).find(([type]) => (props.block as any)[type]());
		if (blockType) {
			toast.warning(blockType[1]);
		} else {
			enableLinkInput();
		}
	}
};

let lastSelection = { from: 0, to: 0 };

watch(
	editorRef,
	(newEditor) => {
		if (newEditor) {
			const { from, to } = newEditor.state.selection;
			lastSelection = { from, to };

			newEditor.on("selectionUpdate", () => {
				if (settingColor.value) return;
				if (isHoveringMenu.value || isMouseDownInMenu.value || isInteractingWithMenu()) return;
				const { from: newFrom, to: newTo } = newEditor.state.selection;
				if (newFrom !== lastSelection.from || newTo !== lastSelection.to) {
					settingLink.value = false;
					textLink.value = "";
					settingColor.value = false;
					lastSelection = { from: newFrom, to: newTo };
				}
			});
		}
	},
	{ immediate: true },
);

debouncedWatch(
	() => [props.canvasProps?.panning, props.canvasProps?.scaling],
	() => {
		nextTick(() => {
			props.editor?.commands.setMeta(bubbleMenuPluginKey, "updatePosition");
		});
	},
);

defineExpose({
	handleKeydown,
});
</script>
