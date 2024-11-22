<template>
	<div class="flex h-screen flex-col items-center bg-gray-100 p-5 dark:bg-zinc-900">
		<div class="relative flex w-full items-center justify-center">
			<router-link
				:to="{ name: 'builder', params: { pageId: route.params.pageId || 'new' } }"
				class="absolute left-5 flex w-fit text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 hover:dark:text-gray-100">
				<FeatherIcon name="arrow-left" class="mr-4 h-4 w-4 cursor-pointer" />
				Back to builder
			</router-link>
			<div class="flex gap-1 text-gray-500 dark:bg-zinc-900 dark:text-zinc-500">
				<div
					class="w-auto cursor-pointer rounded-md p-1 px-[8px]"
					v-for="breakpoint in deviceBreakpoints"
					:key="breakpoint.device"
					:class="{
						'bg-surface-white shadow-sm dark:bg-zinc-700': activeBreakpoint === breakpoint.device,
					}"
					@click.stop="() => setWidth(breakpoint.device)">
					<FeatherIcon
						:name="breakpoint.icon"
						class="h-6 w-5"
						:class="{
							'text-gray-700   dark:text-zinc-50': activeBreakpoint === breakpoint.device,
						}" />
				</div>
			</div>
			<BuilderButton
				variant="solid"
				iconLeft="globe"
				@click="
					() => {
						publishing = true;
						store.publishPage().finally(() => (publishing = false));
					}
				"
				class="absolute right-5 border-0"
				:class="{
					'bg-surface-gray-7 !text-ink-white hover:bg-surface-gray-6':
						!publishing && store.activePage?.draft_blocks,
					'dark:bg-surface-gray-2 dark:text-ink-gray-4': !store.activePage?.draft_blocks,
				}"
				:loading="publishing">
				{{ publishing ? "Publishing" : "Publish" }}
			</BuilderButton>
		</div>
		<div
			class="relative mt-5 flex h-[85vh] bg-white"
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
import router from "@/router";
import useStore from "@/store";
import { posthog } from "@/telemetry";
import { useEventListener } from "@vueuse/core";
import { Ref, computed, onActivated, ref, watch, watchEffect } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
const maxWidth = window.innerWidth * 0.92;
const minWidth = 400;
let previewRoute = ref("");
const width = ref(maxWidth);
const loading = ref(false);
const store = useStore();
const publishing = ref(false);

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

useEventListener(document, "keydown", (ev) => {
	if (ev.key === "Escape" && router.currentRoute.value.name === "preview") {
		history.back();
	}
});

// hack to relay mouseup event from iframe to parent
watchEffect(() => {
	if (previewWindow.value) {
		loading.value = true;
		previewWindow.value.addEventListener("load", () => {
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
		});
	}
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
	let queryParams = {
		page: route.params.pageId,
		...store.routeVariables,
	};
	previewRoute.value = `/api/method/builder.api.get_page_preview_html?${Object.entries(queryParams)
		.map(([key, value]) => `${key}=${value}`)
		.join("&")}`;
};

watch(
	() => route.params.pageId,
	() => {
		setPreviewURL();
	},
	{ immediate: true },
);

onActivated(() => {
	posthog.capture("builder_page_preview_viewed");
});
</script>
