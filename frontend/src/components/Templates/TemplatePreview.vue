<template>
	<div class="flex h-full flex-col overflow-hidden">
		<!-- pt/pr center this row on the dialog's absolute close button (top-5/right-5) -->
		<div class="flex items-center justify-between gap-4 px-8 pb-4 pr-16 pt-5">
			<div class="flex min-w-0 flex-1 items-center">
				<Button icon-left="lucide-arrow-left" variant="ghost" class="-ml-3" @click="$emit('close')">
					Back
				</Button>
			</div>
			<div class="flex items-center gap-1">
				<Button
					v-for="breakpoint in breakpoints"
					:key="breakpoint.device"
					:icon="breakpoint.icon"
					variant="ghost"
					:class="{ '!bg-surface-gray-2': activeBreakpoint === breakpoint.device }"
					@click="activeBreakpoint = breakpoint.device" />
			</div>
			<div class="flex flex-1 justify-end">
				<Button variant="solid" @click="$emit('select', page)">Use template</Button>
			</div>
		</div>
		<div class="flex min-h-0 flex-1 flex-col px-8 pb-8">
			<div
				ref="frameContainer"
				class="relative min-h-0 flex-1 overflow-hidden rounded-lg border border-outline-gray-2">
				<div v-if="loading" class="absolute inset-0 animate-pulse bg-surface-gray-2"></div>
				<iframe
					:src="src"
					class="absolute left-1/2 top-0 origin-top"
					:style="frameStyle"
					@load="loading = false"></iframe>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import { TemplatePageSummary } from "@/types/template";
import { useElementSize } from "@vueuse/core";
import { Button } from "frappe-ui";
import { computed, ref } from "vue";

const props = defineProps<{
	page: TemplatePageSummary;
}>();

defineEmits(["close", "select"]);

const loading = ref(true);

// render the page at the selected device viewport, scaled by a single factor
// (the desktop fit) so the frames stay proportionate across breakpoints
const DESKTOP_WIDTH = 1440;
const breakpoints = [
	{ device: "desktop", icon: "lucide-monitor", width: DESKTOP_WIDTH },
	{ device: "tablet", icon: "lucide-tablet", width: 800 },
	{ device: "mobile", icon: "lucide-smartphone", width: 420 },
];
const activeBreakpoint = ref("desktop");
const viewportWidth = computed(
	() =>
		breakpoints.find((breakpoint) => breakpoint.device === activeBreakpoint.value)?.width || DESKTOP_WIDTH,
);
const frameContainer = ref<HTMLElement | null>(null);
const { width: containerWidth } = useElementSize(frameContainer);
const scale = computed(() => Math.min(1, (containerWidth.value || DESKTOP_WIDTH) / DESKTOP_WIDTH));
const frameStyle = computed(() => ({
	width: `${viewportWidth.value}px`,
	height: `${100 / scale.value}%`,
	transform: `translateX(-50%) scale(${scale.value})`,
}));

// remote hub templates carry an absolute live_url; local "My Templates" render
// through the preview-html endpoint (same one the builder's preview mode embeds)
const src = computed(
	() =>
		props.page.live_url ||
		`/api/method/builder.api.get_page_preview_html?page=${encodeURIComponent(props.page.name)}`,
);
</script>
