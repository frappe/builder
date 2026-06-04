<template>
	<div
		class="flex h-full w-52 shrink-0 flex-col gap-1 overflow-y-auto border-r border-outline-gray-2 bg-surface-gray-1 p-3">
		<span class="mb-2 px-2 text-lg font-semibold text-ink-gray-9">New Page</span>
		<button
			class="flex items-center gap-2 rounded px-2 py-1.5 text-left text-base text-ink-gray-7 hover:bg-surface-gray-2"
			:class="{ '!bg-surface-gray-3 text-ink-gray-9': modelValue === BLANK_GROUP }"
			@click="$emit('update:modelValue', BLANK_GROUP)">
			<FileIcon class="size-4 shrink-0 text-ink-gray-5" />
			<span class="truncate">Blank page</span>
		</button>
		<template v-if="groups.length">
			<span class="mb-1 mt-4 px-2 text-sm font-medium text-ink-gray-5">Templates</span>
			<button
				v-for="group in groups"
				:key="group.name"
				class="flex items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-base text-ink-gray-7 hover:bg-surface-gray-2"
				:class="{ '!bg-surface-gray-3 text-ink-gray-9': modelValue === group.name }"
				@click="$emit('update:modelValue', group.name)">
				<span class="truncate">{{ group.title }}</span>
				<span class="shrink-0 text-sm text-ink-gray-5">{{ group.pages.length }}</span>
			</button>
		</template>
	</div>
</template>
<script setup lang="ts">
import { TemplateGroup } from "@/types/doctypes";
import FileIcon from "~icons/lucide/file";
import { BLANK_GROUP } from "./templateDialogState";

defineProps<{
	groups: TemplateGroup[];
	modelValue: string;
}>();

defineEmits(["update:modelValue"]);
</script>
