<template>
	<div class="group flex w-full cursor-pointer flex-col gap-2" @click="$emit('select', group)">
		<div
			class="relative overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-gray-2 p-1.5 shadow-sm transition duration-150 hover:border-outline-gray-3 hover:shadow-md">
			<img
				:src="group.preview || fallbackImage"
				:alt="group.title"
				onerror="this.src='/assets/builder/images/fallback.png'"
				class="aspect-video w-full rounded-md bg-surface-gray-1 object-cover object-top" />
			<div
				class="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/40 opacity-0 transition-opacity duration-150 group-hover:opacity-100">
				<Button size="sm" variant="solid" @click.stop="$emit('select', group)">View templates</Button>
				<Button v-if="previewPage" size="sm" variant="subtle" @click.stop="openPreview">Preview</Button>
			</div>
		</div>
		<div class="flex items-center justify-between gap-2 px-[2px]">
			<p class="text-sm-medium truncate text-ink-gray-7 group-hover:text-ink-gray-9">
				{{ group.title }}
			</p>
			<span class="shrink-0 text-xs text-ink-gray-4">
				{{ group.pages.length }} {{ group.pages.length === 1 ? "page" : "pages" }}
			</span>
		</div>
	</div>
</template>
<script setup lang="ts">
import router from "@/router";
import { TemplateGroup } from "@/types/doctypes";
import { computed } from "vue";

const props = defineProps<{
	group: TemplateGroup;
}>();

defineEmits(["select"]);

const fallbackImage = "/assets/builder/images/fallback.png";

// preview the group's first page (its card image represents this page)
const previewPage = computed(() => props.group.pages[0] || null);

const openPreview = () => {
	const page = previewPage.value;
	if (!page) return;
	// remote hub templates carry an absolute live_url; local templates use the
	// in-app preview route (the hub page id has no local page to preview)
	const href = page.live_url || router.resolve({ name: "preview", params: { pageId: page.name } }).href;
	window.open(href, "_blank");
};
</script>
