<template>
	<div class="no-scrollbar flex-1 overflow-y-auto px-8 pb-8">
		<!-- loading -->
		<div v-if="loading" class="grid gap-x-4 gap-y-5 auto-fill-[220px]">
			<div v-for="i in 6" :key="i" class="flex flex-col gap-2">
				<div class="aspect-video w-full animate-pulse rounded-lg bg-surface-gray-2"></div>
				<div class="h-3.5 w-2/3 animate-pulse rounded bg-surface-gray-2"></div>
			</div>
		</div>
		<!-- blank page + template pages -->
		<div v-else class="grid gap-x-4 gap-y-5 auto-fill-[220px]">
			<BlankPageCard label="Blank Page" @click="$emit('blank')" />
			<TemplatePageCard
				v-for="page in group?.pages"
				:key="page.name"
				:page="page"
				@select="(page: TemplatePageSummary) => $emit('select', page)"
				@edit="(page: TemplatePageSummary) => $emit('edit', page)"
				@preview="(page: TemplatePageSummary) => $emit('preview', page)"></TemplatePageCard>
		</div>
	</div>
</template>
<script setup lang="ts">
import type { TemplateGroup, TemplatePageSummary } from "@/types/template";
import BlankPageCard from "./BlankPageCard.vue";
import TemplatePageCard from "./TemplatePageCard.vue";

defineProps<{
	group: TemplateGroup | null;
	loading: boolean;
}>();

defineEmits(["select", "blank", "edit", "preview"]);
</script>
