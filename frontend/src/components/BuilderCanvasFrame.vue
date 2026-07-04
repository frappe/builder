<template>
	<iframe
		ref="iframe"
		:srcdoc="FRAME_DOCUMENT"
		:title="`Canvas frame for ${breakpoint}`"
		:data-canvas-breakpoint="breakpoint"
		class="block border-0 bg-transparent"
		:style="{
			width: `${width}px`,
			height: `${height}px`,
			background,
			colorScheme: dark ? 'dark' : 'light',
		}" />
	<Teleport v-if="target" :to="target">
		<div
			ref="canvasRoot"
			class="canvas canvas-container relative flex w-full contain-layout"
			:class="{ 'scheme-dark': dark }"
			:data-breakpoint="breakpoint"
			:data-builder-canvas="canvasId"
			:style="rootStyle">
			<slot />
		</div>
	</Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

const FRAME_DOCUMENT = "<!doctype html><html><head></head><body></body></html>";

const props = withDefaults(
	defineProps<{
		breakpoint: string;
		width: number;
		background: string;
		canvasId: string;
		canvasStyles?: Record<string, any>;
		dark?: boolean;
	}>(),
	{
		canvasStyles: () => ({}),
		dark: false,
	},
);

const emit = defineEmits<{
	ready: [breakpoint: string, doc: Document, root: HTMLElement, iframe: HTMLIFrameElement];
	dispose: [breakpoint: string, doc: Document | null];
}>();

const iframe = ref<HTMLIFrameElement | null>(null);
const canvasRoot = ref<HTMLElement | null>(null);
const target = ref<HTMLElement | null>(null);
const height = ref(1);
let resizeObserver: ResizeObserver | null = null;
let editorObserver: MutationObserver | null = null;
let currentDocument: Document | null = null;

const rootStyle = computed(() => ({
	...props.canvasStyles,
	background: props.background,
	minHeight: props.canvasStyles.minHeight || "100%",
}));

function syncDocumentChrome(doc: Document) {
	doc.documentElement.dataset.theme = document.documentElement.dataset.theme || "";
	doc.documentElement.className = document.documentElement.className;
	doc.body.className = document.body.className;
	doc.body.style.margin = "0";
	doc.body.style.width = "100%";
	doc.body.style.minHeight = "100%";
	doc.body.style.overflow = "visible";
}

function cloneEditorStyles(doc: Document) {
	doc.head.querySelectorAll("[data-builder-frame-style]").forEach((node) => node.remove());
	document.head
		.querySelectorAll<HTMLLinkElement | HTMLStyleElement>("link[rel='stylesheet'], style")
		.forEach((source) => {
			const clone = source.cloneNode(true) as HTMLLinkElement | HTMLStyleElement;
			clone.setAttribute("data-builder-frame-style", "");
			doc.head.appendChild(clone);
		});
}

function updateHeight() {
	const doc = currentDocument;
	if (!doc || !canvasRoot.value) return;
	height.value = Math.max(
		1,
		Math.ceil(canvasRoot.value.scrollHeight),
		Math.ceil(doc.body.scrollHeight),
		Math.ceil(doc.documentElement.scrollHeight),
	);
}

function cleanupFrame() {
	resizeObserver?.disconnect();
	resizeObserver = null;
	editorObserver?.disconnect();
	editorObserver = null;
	if (currentDocument) emit("dispose", props.breakpoint, currentDocument);
	currentDocument = null;
	target.value = null;
}

async function attachFrame() {
	cleanupFrame();
	const frame = iframe.value;
	const doc = frame?.contentDocument;
	if (!frame || !doc || doc.readyState === "loading") return;

	currentDocument = doc;
	syncDocumentChrome(doc);
	cloneEditorStyles(doc);
	target.value = doc.body;
	await nextTick();
	if (!canvasRoot.value) return;

	const FrameResizeObserver = doc.defaultView?.ResizeObserver || ResizeObserver;
	resizeObserver = new FrameResizeObserver(updateHeight);
	resizeObserver.observe(canvasRoot.value);
	resizeObserver.observe(doc.body);
	updateHeight();

	editorObserver = new MutationObserver((mutations) => {
		if (!currentDocument) return;
		if (mutations.some(({ target }) => document.head.contains(target))) {
			cloneEditorStyles(currentDocument);
		}
		if (mutations.some(({ type }) => type === "attributes")) {
			syncDocumentChrome(currentDocument);
		}
	});
	editorObserver.observe(document.head, { childList: true, subtree: true, characterData: true });
	editorObserver.observe(document.documentElement, {
		attributes: true,
		attributeFilter: ["class", "data-theme"],
	});
	editorObserver.observe(document.body, { attributes: true, attributeFilter: ["class"] });

	emit("ready", props.breakpoint, doc, canvasRoot.value, frame);
}

watch(
	iframe,
	(frame, previous) => {
		previous?.removeEventListener("load", attachFrame);
		frame?.addEventListener("load", attachFrame);
		attachFrame();
	},
	{ flush: "post" },
);

onBeforeUnmount(() => {
	iframe.value?.removeEventListener("load", attachFrame);
	cleanupFrame();
});
</script>
