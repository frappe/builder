<template>
	<div class="no-scrollbar flex-1 overflow-y-auto px-8 pb-8">
		<!-- loading -->
		<div v-if="loading" class="grid gap-3 auto-fill-[190px]">
			<div v-for="i in 6" :key="i" class="flex flex-col gap-2">
				<div class="aspect-video w-full animate-pulse rounded-md bg-surface-gray-2"></div>
				<div class="h-3.5 w-2/3 animate-pulse rounded bg-surface-gray-2"></div>
			</div>
		</div>
		<!-- blank page -->
		<div v-else-if="blank" class="grid gap-3 auto-fill-[190px]">
			<button
				class="flex aspect-video w-full flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-outline-gray-3 text-ink-gray-5 transition-colors duration-150 hover:border-outline-gray-4 hover:bg-surface-gray-1 hover:text-ink-gray-7"
				@click="$emit('blank')">
				<PlusIcon class="size-5" />
				<span class="text-sm">Blank page</span>
			</button>
		</div>
		<!-- template pages -->
		<div v-else-if="group?.pages.length" class="grid gap-3 auto-fill-[190px]">
			<TemplatePageCard
				v-for="page in group.pages"
				:key="page.name"
				:page="page"
				@select="(page: TemplatePageSummary) => $emit('select', page)"
				@edit="(page: TemplatePageSummary) => $emit('edit', page)"></TemplatePageCard>
		</div>
		<!-- empty -->
		<div v-else class="flex h-full items-center justify-center">
			<p class="text-base text-ink-gray-5">No templates in this group yet.</p>
		</div>
	</div>
</template>
<script setup lang="ts">
import { TemplateGroup, TemplatePageSummary } from "@/types/doctypes";
import PlusIcon from "~icons/lucide/plus";
import TemplatePageCard from "./TemplatePageCard.vue";

defineProps<{
	group: TemplateGroup | null;
	blank: boolean;
	loading: boolean;
}>();

defineEmits(["select", "edit", "blank"]);
</script>
