<template>
	<bubble-menu
		ref="menu"
		:editor="editor"
		:tippy-options="bubbleMenuOptions.tippyOptions"
		v-if="editor"
		class="rounded-md border border-outline-gray-3 bg-surface-white p-1 text-lg text-ink-gray-9 shadow-2xl"
		:should-show="bubbleMenuOptions.shouldShow">
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
			<div v-show="!block.isHeader()">
				<ColorPicker
					:modelValue="selectedColor"
					@update:modelValue="setTextColor"
					:show-input="true"
					placement="top"
					:appendTo="overlayElement"
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
		</div>
	</bubble-menu>
</template>

<script setup lang="ts">
import type Block from "@/block";
import ColorPicker from "@/components/Controls/ColorPicker.vue";
import Input from "@/components/Controls/Input.vue";
import StrikeThroughIcon from "@/components/Icons/StrikeThrough.vue";
import { BubbleMenu, type Editor } from "@tiptap/vue-3";
import { vOnClickOutside } from "@vueuse/components";
import { debounce } from "frappe-ui";
import { computed, nextTick, ref, watch, type Ref } from "vue";
import { toast } from "vue-sonner";

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

const editorRef = computed(() => props.editor);
const isEditableRef = computed(() => props.isEditable);

const selectedColor = computed(() => {
	if (props.editor?.isActive("textStyle")) {
		return props.editor.getAttributes("textStyle").color || "#000000";
	}
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

watch(
	editorRef,
	(newEditor) => {
		if (newEditor) {
			newEditor.on("selectionUpdate", () => {
				settingLink.value = false;
				textLink.value = "";
			});
		}
	},
	{ immediate: true },
);

const bubbleMenuOptions = {
	tippyOptions: {
		appendTo: props.overlayElement,
		interactive: true,
		onCreate: (instance: any) => {
			watch(
				() => props.canvasProps,
				() => {
					if (props.canvasProps?.panning || props.canvasProps?.scaling) {
						instance.hide();
					} else {
						instance.show();
					}
				},
				{ deep: true },
			);
		},
	},
	shouldShow: () => isEditableRef.value,
};

defineExpose({
	handleKeydown,
});
</script>
