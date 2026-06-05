<template>
	<div class="flex w-48 shrink-0 flex-col gap-5 overflow-y-auto bg-surface-gray-1 p-4 px-2">
		<span class="px-2 text-lg font-semibold text-ink-gray-9">New page</span>
		<div class="flex flex-col">
			<Button
				:variant="modelValue === BLANK_GROUP ? 'subtle' : 'ghost'"
				icon-left="lucide-file"
				class="!justify-start"
				:class="{ '!bg-surface-gray-3': modelValue === BLANK_GROUP }"
				@click="$emit('update:modelValue', BLANK_GROUP)">
				Blank page
			</Button>
		</div>
		<div class="flex flex-col" v-if="groups.length">
			<span class="mb-2 px-2 text-base font-medium text-ink-gray-5">Templates</span>
			<Button
				v-for="group in groups"
				:key="group.name"
				:variant="modelValue === group.name ? 'subtle' : 'ghost'"
				icon-left="lucide-layout-template"
				class="!justify-start"
				:class="{ '!bg-surface-gray-3': modelValue === group.name }"
				@click="$emit('update:modelValue', group.name)">
				{{ group.title }}
			</Button>
		</div>
	</div>
</template>
<script setup lang="ts">
import { TemplateGroup } from "@/types/doctypes";
import { BLANK_GROUP } from "./templateDialogState";

defineProps<{
	groups: TemplateGroup[];
	modelValue: string;
}>();

defineEmits(["update:modelValue"]);
</script>
