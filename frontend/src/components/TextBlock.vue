<template>
	<component
		:is="block.getTag()"
		ref="component"
		@click.stop
		@dblclick.stop
		:key="editor"
		class="__text_block__ shrink-0">
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
						{ deep: true }
					);
				},
			}"
			v-if="editor"
			class="z-50 rounded-md border border-gray-300 bg-white p-1 text-lg">
			<div v-if="settingLink" class="flex">
				<Input
					v-model="textLink"
					placeholder="https://example.com"
					class="link-input w-56 text-sm"
					@keydown.enter="
						() => {
							if (!linkInput) return;
							setLink(linkInput?.getInputValue());
						}
					"
					ref="linkInput"></Input>
				<Button @click="setLink" class="ml-1">
					<FeatherIcon class="h-3 w-3" name="check" />
				</Button>
			</div>
			<div v-show="!settingLink" class="flex gap-1">
				<button
					@click="editor.chain().focus().toggleBold().run()"
					class="rounded px-2 py-1 hover:bg-gray-100"
					:class="{ 'bg-gray-200': editor.isActive('bold') }">
					<FeatherIcon class="h-3 w-3" name="bold" />
				</button>
				<button
					@click="editor.chain().focus().toggleItalic().run()"
					class="rounded px-2 py-1 hover:bg-gray-100"
					:class="{ 'bg-gray-200': editor.isActive('italic') }">
					<FeatherIcon class="h-3 w-3" name="italic" />
				</button>
				<button
					@click="editor.chain().focus().toggleStrike().run()"
					class="rounded px-2 py-1 hover:bg-gray-100"
					:class="{ 'bg-gray-200': editor.isActive('strike') }">
					<StrikeThroughIcon />
				</button>
				<button
					@click="
						() => {
							if (!editor) return;
							if (editor.isActive('link')) {
								editor.chain().focus().unsetLink().run();
							} else {
								enableLinkInput();
							}
						}
					"
					class="rounded px-2 py-1 hover:bg-gray-100"
					:class="{ 'bg-gray-200': editor.isActive('link') }">
					<FeatherIcon class="h-3 w-3" name="link" />
				</button>
			</div>
		</bubble-menu>
		<editor-content
			@click="handleClick"
			:editor="editor"
			v-if="editor && showEditor"
			class="relative z-50"
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
import { BubbleMenu, Editor, EditorContent } from "@tiptap/vue-3";
import { Input } from "frappe-ui";
import { Ref, computed, inject, nextTick, onBeforeMount, onBeforeUnmount, ref, watch } from "vue";
import StrikeThroughIcon from "./Icons/StrikeThrough.vue";

const overlayElement = document.querySelector("#overlay") as HTMLElement;

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

const canvasProps = !props.preview ? (inject("canvasProps") as CanvasProps) : null;

const settingLink = ref(false);
const textLink = ref("");
const linkInput = ref(null) as Ref<typeof Input | null>;

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

const textContent = computed(() => {
	let innerHTML = props.block.getInnerHTML();
	if (props.data) {
		if (props.block.getDataKey("property") === "innerHTML") {
			innerHTML = getDataForKey(props.data, props.block.getDataKey("key")) || innerHTML;
		}
	}
	return innerHTML;
});

let editor: Ref<Editor | null> = ref(null);

const isEditable = computed(() => {
	return store.editableBlock === props.block;
});

const showEditor = computed(() => {
	return !((props.block.isLink() || props.block.isButton()) && props.block.hasChildren());
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
			store.activeCanvas?.history.pause();
			editor.value?.commands.focus("all");
		} else {
			store.activeCanvas?.history.resume();
		}
	},
	{ immediate: true }
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
		() => store.isSelected(props.block.blockId),
		() => {
			// only load editor if block is selected for performance reasons
			if (store.isSelected(props.block.blockId) && !blockController.multipleBlocksSelected()) {
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
					],
					onUpdate({ editor }) {
						const innerHTML = editor.isEmpty ? "" : editor.getHTML();
						if (props.block.getInnerHTML() === innerHTML) {
							return;
						}
						props.block.setInnerHTML(innerHTML);
					},
					onSelectionUpdate: ({ editor }) => {
						settingLink.value = false;
						textLink.value = "";
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
		},
		{ immediate: true }
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

const handleKeydown = (e: KeyboardEvent) => {
	if (e.key === "k" && e.metaKey) {
		enableLinkInput();
	}
};

const enableLinkInput = () => {
	settingLink.value = true;
	nextTick(() => {
		if (linkInput.value) {
			const input = document.querySelector(".link-input") as HTMLInputElement;
			input.focus();
		}
	});
};
</script>
