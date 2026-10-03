<template>
	<div class="flex h-screen flex-col bg-surface-base">
		<div v-if="!isFullscreen" class="grid grid-cols-[1fr_auto_1fr] items-center border-b px-3 py-2">
			<div class="flex items-center gap-1">
				<Button
					variant="ghost"
					:icon-left="actions.back.icon"
					:label="actions.back.label"
					@click="actions.back.onClick" />
				<Button
					v-for="action in headerActions"
					:key="action.label"
					variant="ghost"
					:icon="action.icon"
					:label="action.label"
					:tooltip="action.label"
					@click="action.onClick" />
			</div>
			<div class="flex gap-1">
				<div
					class="w-auto cursor-pointer rounded-5 p-1 px-[8px]"
					v-for="breakpoint in deviceBreakpoints"
					:key="breakpoint.device"
					:class="{
						'bg-surface-gray-2': activeBreakpoint === breakpoint.device,
					}"
					@click.stop="() => setWidth(breakpoint.device)">
					<span
						:class="[
							breakpoint.icon,
							'h-6 w-5 text-ink-gray-4',
							{ 'text-ink-gray-9': activeBreakpoint === breakpoint.device },
						]"
						aria-hidden="true" />
				</div>
			</div>
			<div class="flex items-center justify-end gap-4">
				<Button
					variant="ghost"
					class="text-ink-gray-8"
					:icon="actions.darkMode.icon"
					:label="actions.darkMode.label"
					:tooltip="actions.darkMode.label"
					@click="actions.darkMode.onClick" />
				<PublishButton />
			</div>
		</div>
		<div
			ref="previewContainer"
			class="relative flex flex-1 justify-center overflow-hidden bg-surface-gray-1"
			:class="{ 'px-6 pt-6': !isFullscreen }">
			<PreviewFloatingToolbar v-if="isFullscreen" :container="previewContainer" :actions="toolbarActions" />
			<div class="relative h-full bg-white" :style="{ width: frameWidth }">
				<iframe
					:src="previewRoute"
					frameborder="0"
					v-if="previewRoute"
					class="h-full w-full"
					ref="previewFrame"></iframe>
				<div v-if="loading || resizing" class="absolute inset-0"></div>
				<template v-if="!isFullscreen">
					<PanelResizer
						v-for="side in resizerSides"
						:key="side"
						:side="side"
						class="!top-1/2 !h-8 -translate-y-1/2"
						:class="side === 'left' ? '!-left-4' : '!-right-4'"
						:dimension="width"
						:minDimension="minWidth"
						:maxDimension="maxWidth"
						:resizeSensitivity="2"
						ref="resizers"
						@resize="(val) => (width = val)">
						<div class="h-full w-full rounded-full bg-surface-gray-4 hover:bg-surface-gray-5"></div>
					</PanelResizer>
				</template>
			</div>
		</div>
	</div>
</template>
<script lang="ts" setup>
import { __ } from "@/translation";
import PanelResizer from "@/components/PanelResizer.vue";
import PreviewFloatingToolbar from "@/components/PreviewFloatingToolbar.vue";
import PublishButton from "@/components/PublishButton.vue";
import { webPages } from "@/data/webPage";
import router from "@/router";
import useBuilderStore from "@/stores/builderStore";
import usePageStore, { DETACHED_PREVIEW_CHANNEL } from "@/stores/pageStore";
import { BuilderPage } from "@/types/doctypes";
import { Button, useKeyboardShortcut } from "frappe-ui";
import { useTelemetry } from "@framework/ui/telemetry";
import { useDebounceFn, useEventListener, useStorage } from "@vueuse/core";
import { Ref, computed, onActivated, onDeactivated, ref, watch } from "vue";
import { useRoute } from "vue-router";

const { capture } = useTelemetry();

const route = useRoute();
const pageStore = usePageStore();
const builderStore = useBuilderStore();
const maxWidth = window.innerWidth * 0.92;
const minWidth = 400;
let previewRoute = ref("");
const width = ref(maxWidth);

// covers the iframe until onPreviewLoad forwards its mouse events
const loading = ref(true);

const actions = computed(() => ({
	back: {
		icon: canGoBack.value ? "lucide-arrow-left" : "lucide-pencil",
		label: canGoBack.value ? __("Back") : __("Edit"),
		onClick: goBack,
	},
	reload: { icon: "lucide-rotate-cw", label: __("Reload"), onClick: setPreviewURL },
	enterFullscreen: {
		icon: "lucide-maximize-2",
		label: __("Full screen"),
		onClick: () => setFullscreen(true),
	},
	exitFullscreen: { icon: "lucide-tablet-smartphone", label: __("Show Breakpoints"), onClick: () => setFullscreen(false) },
	detach: { icon: "lucide-external-link", label: __("Open in New Tab"), onClick: detachPreview },
	darkMode: {
		icon: isDark.value ? "lucide-sun" : "lucide-moon",
		label: __("Toggle Dark Mode"),
		onClick: toggleDarkMode,
	},
}));

const deviceBreakpoints = [
	{
		icon: "lucide-monitor",
		device: "desktop",
		width: 1400,
	},
	{
		icon: "lucide-tablet",
		device: "tablet",
		width: 800,
	},
	{
		icon: "lucide-smartphone",
		device: "mobile",
		width: 420,
	},
];

const previewContainer = ref<HTMLElement | null>(null);
const previewFrame = ref(null) as Ref<HTMLIFrameElement | null>;

// not lastFullscreen: a preview from the editor never opens in full screen
const isFullscreen = ref(false);
// for a preview opened by its own link
const lastFullscreen = useStorage("previewFullscreen", false);
const setFullscreen = (fullscreen: boolean) => {
	isFullscreen.value = fullscreen;
	lastFullscreen.value = fullscreen;
};

// the opener of a preview from the editor can be the detached tab
const goBack = () => {
	if (!cameFromEditor.value && pageStore.focusEditorTab()) return;
	router.push({ name: "builder", params: { pageId: route.params.pageId || "new" } });
};

// a blocked popup leaves this the only preview, so stay
const detachPreview = () => {
	if (pageStore.detachPreview(route.params.pageId as string)) goBack();
};

const cameFromEditor = ref(false);
const hasEditorTab = ref(false);

useEventListener(new BroadcastChannel(DETACHED_PREVIEW_CHANNEL), "message", () => {
	if (route.name === "preview" && hasEditorTab.value && !cameFromEditor.value) {
		pageStore.announceDetachedPreview(route.params.pageId as string);
	}
});
const canGoBack = computed(() => cameFromEditor.value || hasEditorTab.value);
const frameWidth = computed(() => (isFullscreen.value ? "100%" : `${width.value}px`));

const resizerSides = ["left", "right"] as const;
const resizers = ref<InstanceType<typeof PanelResizer>[]>([]);

const resizing = computed(() => resizers.value.some((resizer) => resizer.dragActive));

const activeBreakpoint = computed(() => {
	const tabletBreakpoint = deviceBreakpoints.find((b) => b.device === "tablet");
	const mobileBreakpoint = deviceBreakpoints.find((b) => b.device === "mobile");
	if (width.value <= (mobileBreakpoint?.width || minWidth)) {
		return "mobile";
	}
	if (width.value <= (tabletBreakpoint?.width || maxWidth)) {
		return "tablet";
	}
	return "desktop";
});

// Toggle the previewed PAGE's dark mode (shared with the canvas via
// canvasDarkMode), not the Builder editor's UI theme.
const isDark = computed(() => builderStore.canvasDarkMode);

const toggleDarkMode = () => {
	builderStore.canvasDarkMode = !builderStore.canvasDarkMode;
};

useKeyboardShortcut({
	combo: "Escape",
	description: __("Back to Builder"),
	group: __("Navigation"),
	handler: () => {
		if (isFullscreen.value) setFullscreen(false);
		else if (router.currentRoute.value.name === "preview") history.back();
	},
	enabled: () => router.currentRoute.value.name === "preview",
});

useKeyboardShortcut({
	combo: "Mod+P",
	description: __("Back to Builder"),
	group: __("Navigation"),
	handler: goBack,
	enabled: () => router.currentRoute.value.name === "preview",
});

const applyColorSchemeToIframe = (scheme: "dark" | "light") => {
	try {
		const win = previewFrame.value?.contentWindow;
		const doc = win?.document;
		if (doc && doc.documentElement) {
			doc.documentElement.setAttribute("data-prefers-color-scheme", scheme);
		}
	} catch (e) {
		// ignore cross-origin or timing errors
	}
};

// the preview reloads on each save, so keep the scroll position
const scrollStorageKey = () => `previewScroll:${route.params.pageId}`;

const saveScrollPosition = useDebounceFn(() => {
	const scrollY = previewFrame.value?.contentWindow?.scrollY;
	if (scrollY !== undefined) sessionStorage.setItem(scrollStorageKey(), String(scrollY));
}, 200);

const restoreScrollPosition = () => {
	const scrollY = Number(sessionStorage.getItem(scrollStorageKey()));
	// "instant" overrides a smooth scroll-behavior on the page
	if (scrollY) previewFrame.value?.contentWindow?.scrollTo({ top: scrollY, behavior: "instant" });
};

// each reload replaces the document, so add the listeners again
const onPreviewLoad = () => {
	loading.value = false;
	const previewDocument = previewFrame.value?.contentWindow?.document;
	if (!previewDocument) return;
	// without these, a panel drag over the iframe gets stuck
	for (const type of ["mousedown", "mouseup", "mousemove"]) {
		previewDocument.addEventListener(type, (event) =>
			document.dispatchEvent(new MouseEvent(type, event as MouseEvent)),
		);
	}
	// forward Mod+P from the iframe and block print, before the page can stop the event
	previewDocument.addEventListener(
		"keydown",
		(event) => {
			if (event.key.toLowerCase() !== "p" || !(event.ctrlKey || event.metaKey)) return;
			event.preventDefault();
			document.dispatchEvent(new KeyboardEvent("keydown", event));
		},
		{ capture: true },
	);
	applyColorSchemeToIframe(isDark.value ? "dark" : "light");
	restoreScrollPosition();
	previewDocument.addEventListener("scroll", saveScrollPosition, { passive: true });
};

useEventListener(previewFrame, "load", onPreviewLoad);

watch(isDark, async (val) => {
	setPreviewURL();
	setTimeout(() => {
		applyColorSchemeToIframe(val ? "dark" : "light");
	}, 100);
});

const setWidth = (device: string) => {
	const breakpoint = deviceBreakpoints.find((b) => b.device === device);
	if (breakpoint) {
		if (breakpoint.device === "desktop") {
			width.value = maxWidth;
		} else {
			width.value = breakpoint.width;
		}
	}
};

const setPreviewURL = () => {
	let queryParams: Record<string, any> = {
		page: route.params.pageId,
		...pageStore.routeVariables,
		prefers_color_scheme: isDark.value ? "dark" : "light",
		reloaded_at: Date.now(),
	};
	previewRoute.value = `/api/method/builder.api.get_page_preview_html?${Object.entries(queryParams)
		.map(([key, value]) => `${key}=${value}`)
		.join("&")}`;
};

const headerActions = computed(() => [
	actions.value.enterFullscreen,
	...(cameFromEditor.value ? [actions.value.detach] : []),
]);

const toolbarActions = computed(() => [
	actions.value.back,
	actions.value.reload,
	actions.value.exitFullscreen,
	actions.value.darkMode,
]);

const reloadOnPageSave = (event: { doctype: string; name: string; modified: string }) => {
	if (event.doctype !== "Builder Page" || event.name !== route.params.pageId) return;
	setPreviewURL();
	if (!cameFromEditor.value) syncPageStore();
};

// no editor in this tab keeps the page store current
const syncPageStore = () => {
	const currentModified = pageStore.activePage?.modified;
	webPages.fetchOne.submit(pageStore.activePage?.name).then((doc: BuilderPage[] | null) => {
		if (currentModified !== doc?.[0]?.modified) {
			pageStore.setPage(route.params.pageId as string, false, route.query);
		}
	});
};

onDeactivated(() => {
	builderStore.realtime.off("doc_update", reloadOnPageSave);
	// an editor in this tab keeps using the subscription
	if (!cameFromEditor.value) {
		builderStore.realtime.doc_unsubscribe("Builder Page", route.params.pageId as string);
	}
});

onActivated(() => {
	const pageId = route.params.pageId as string;
	const previousPath = window.history.state?.back;

	cameFromEditor.value = typeof previousPath === "string" && router.resolve(previousPath).name === "builder";
	hasEditorTab.value = Boolean(pageStore.getEditorTab());
	isFullscreen.value = cameFromEditor.value ? false : lastFullscreen.value;
	// a detached or bookmarked preview has no editor to load the page first
	if (pageStore.activePage?.name !== pageId) {
		pageStore.loadRouteVariables(pageId);
		pageStore.setActivePage(pageId);
	}
	
	builderStore.realtime.doc_subscribe("Builder Page", pageId);
	builderStore.realtime.on("doc_update", reloadOnPageSave);
	setPreviewURL();
	capture("builder_page_preview_viewed");
});
</script>
