<template>
	<div class="flex h-screen flex-col items-center bg-surface-white py-2">
		<div class="space-between relative flex w-full items-center justify-between px-3 py-1">
			<router-link
				:to="{ name: 'builder', params: { pageId: route.params.pageId || 'new' } }"
				class="flex w-fit text-sm text-ink-gray-7 hover:text-ink-gray-9">
				<FeatherIcon name="arrow-left" class="mr-4 h-4 w-4 cursor-pointer" />
				Back to builder
			</router-link>
			<div class="flex gap-1">
				<div
					class="w-auto cursor-pointer rounded-md p-1 px-[8px]"
					v-for="breakpoint in deviceBreakpoints"
					:key="breakpoint.device"
					:class="{
						'bg-surface-white': activeBreakpoint === breakpoint.device,
					}"
					@click.stop="() => setWidth(breakpoint.device)">
					<FeatherIcon
						:name="breakpoint.icon"
						class="h-6 w-5 text-ink-gray-4"
						:class="{
							'text-ink-gray-9': activeBreakpoint === breakpoint.device,
						}" />
				</div>
			</div>
			<div class="flex items-center gap-4">
				<Tooltip text="Toggle Dark Mode" :hoverDelay="0.6">
					<Button
						variant="ghost"
						:icon="isDark ? 'sun' : 'moon'"
						class="h-8 w-8 cursor-pointer text-ink-gray-8 outline-none"
						@click="() => transitionTheme(toggleDark)" />
				</Tooltip>
				<PublishButton></PublishButton>
			</div>
		</div>
		<div
			class="relative mt-5 flex h-[calc(100vh-100px)] bg-white"
			:style="{
				width: width + 'px',
			}">
			<PanelResizer
				class="ml-[-12px]"
				side="left"
				:dimension="width"
				:minDimension="minWidth"
				:maxDimension="maxWidth"
				:resizeSensitivity="2"
				ref="leftPanelRef"
				@resize="(val) => (width = val)">
				<div class="resize-handler-left h-full w-2 rounded-sm bg-surface-gray-2"></div>
			</PanelResizer>
			<iframe
				:src="previewRoute"
				frameborder="0"
				v-if="previewRoute"
				class="flex-1 rounded-sm"
				ref="previewWindow"></iframe>
			<div v-if="loading || resizing" class="absolute flex h-full w-full items-center justify-center"></div>
			<PanelResizer
				class="mr-[-8px]"
				side="right"
				:dimension="width"
				:minDimension="minWidth"
				:maxDimension="maxWidth"
				:resizeSensitivity="2"
				ref="rightPanelRef"
				@resize="(val) => (width = val)">
				<div class="resize-handler-left h-full w-2 rounded-sm bg-surface-gray-2"></div>
			</PanelResizer>
		</div>
	</div>
</template>
<script lang="ts" setup>
import PanelResizer from "@/components/PanelResizer.vue";
import PublishButton from "@/components/PublishButton.vue";
import router from "@/router";
import usePageStore from "@/stores/pageStore";
import { posthog } from "@/telemetry";
import { useDark, useEventListener, useToggle } from "@vueuse/core";
import { Tooltip } from "frappe-ui";
import { Ref, computed, onActivated, ref, watch, watchEffect } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
const maxWidth = window.innerWidth * 0.92;
const minWidth = 400;
let previewRoute = ref("");
const width = ref(maxWidth);
const loading = ref(false);
const pageStore = usePageStore();

const deviceBreakpoints = [
	{
		icon: "monitor",
		device: "desktop",
		width: 1400,
	},
	{
		icon: "tablet",
		device: "tablet",
		width: 800,
	},
	{
		icon: "smartphone",
		device: "mobile",
		width: 420,
	},
];

const leftPanelRef = ref<InstanceType<typeof PanelResizer> | null>(null);
const rightPanelRef = ref<InstanceType<typeof PanelResizer> | null>(null);

const resizing = computed(() => leftPanelRef.value?.dragActive || rightPanelRef.value?.dragActive);

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

const previewWindow = ref(null) as Ref<HTMLIFrameElement | null>;
const isDark = useDark({
	attribute: "data-theme",
});

const toggleDark = useToggle(isDark);

const transitionTheme = (toggle: () => void) => {
	const doc: any = document;
	if (doc.startViewTransition && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
		doc.startViewTransition(() => {
			toggle();
		});
	} else {
		toggle();
	}
};

useEventListener(document, "keydown", (ev) => {
	if (ev.key === "Escape" && router.currentRoute.value.name === "preview") {
		history.back();
	}
});

const applyColorSchemeToIframe = (scheme: "dark" | "light") => {
	try {
		const win = previewWindow.value?.contentWindow;
		const doc = win?.document;
		if (doc && doc.documentElement) {
			doc.documentElement.setAttribute("data-prefers-color-scheme", scheme);
		}
	} catch (e) {
		// ignore cross-origin or timing errors
	}
};

watchEffect(() => {
	if (previewWindow.value) {
		loading.value = true;
		previewWindow.value.addEventListener(
			"load",
			() => {
				setTimeout(() => {
					loading.value = false;
				}, 100);
				previewWindow.value?.addEventListener("mousedown", (ev) => {
					document.dispatchEvent(new MouseEvent("mousedown", ev));
				});
				previewWindow.value?.contentWindow?.document.addEventListener("mouseup", (ev) => {
					document.dispatchEvent(new MouseEvent("mouseup", ev));
				});
				previewWindow.value?.contentWindow?.document.addEventListener("mousemove", (ev) => {
					document.dispatchEvent(new MouseEvent("mousemove", ev));
				});

				applyColorSchemeToIframe(isDark.value ? "dark" : "light");
			},
			{ once: true },
		);
	}
});

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
	};
	previewRoute.value = `/api/method/builder.api.get_page_preview_html?${Object.entries(queryParams)
		.map(([key, value]) => `${key}=${value}`)
		.join("&")}`;
};

onActivated(() => {
	setPreviewURL();
	posthog.capture("builder_page_preview_viewed");
});
</script>
