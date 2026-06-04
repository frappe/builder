<template>
	<div class="group flex w-full flex-col gap-2">
		<div
			class="relative cursor-pointer overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-gray-2 p-1.5 shadow-sm transition duration-150 hover:border-outline-gray-3 hover:shadow-md"
			@click="$emit('select', page)">
			<img
				:src="page.preview || fallbackImage"
				:alt="page.page_title || page.name"
				onerror="this.src='/assets/builder/images/fallback.png'"
				class="aspect-video w-full rounded-md bg-surface-gray-1 object-cover object-top" />
			<div
				class="absolute inset-0 flex items-center justify-center gap-2 bg-black/40 opacity-0 transition-opacity duration-150 group-hover:opacity-100">
				<Button size="sm" variant="subtle" @click.stop="openPreview">Preview</Button>
				<Button size="sm" variant="solid" @click.stop="$emit('select', page)">Use template</Button>
			</div>
		</div>
		<div class="flex items-center justify-between gap-2 px-[2px]">
			<p class="truncate text-base font-medium text-ink-gray-7 group-hover:text-ink-gray-9">
				{{ page.page_title || page.name }}
			</p>
			<Button
				v-if="isDeveloperMode"
				size="sm"
				variant="ghost"
				icon="lucide-pencil"
				title="Edit template"
				class="shrink-0 !text-ink-gray-5 hover:!text-ink-gray-9"
				@click.stop="$emit('edit', page)"></Button>
		</div>
	</div>
</template>
<script setup lang="ts">
import router from "@/router";
import { TemplatePageSummary } from "@/types/doctypes";

const props = defineProps<{
	page: TemplatePageSummary;
}>();

defineEmits(["select", "edit"]);

const fallbackImage = "/assets/builder/images/fallback.png";
const isDeveloperMode = Boolean(window.is_developer_mode);

const openPreview = () => {
	const href = router.resolve({ name: "preview", params: { pageId: props.page.name } }).href;
	window.open(href, "_blank");
};
</script>
