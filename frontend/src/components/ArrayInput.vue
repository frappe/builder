<template>
	<Popover :offset="20" side="left" align="center" bare>
		<template #trigger>
			<div class="relative flex w-full gap-2">
				<div v-if="label" class="flex w-1/3 min-w-[88px] shrink-0 items-center">
					<InputLabel class="w-full truncate">
						{{ label }}
					</InputLabel>
				</div>
				<div class="relative w-full">
					<Button class="!w-full w-full" variant="subtle" icon="lucide-pencil" />
				</div>
			</div>
		</template>
		<template #default>
			<div
				@click.stop
				@mousedown.stop
				class="flex max-h-60 flex-col gap-3 overflow-auto rounded-lg bg-surface-base p-4 shadow-lg"
				:class="itemType === 'image' ? 'w-72' : 'w-60'">
				<div class="text-sm text-ink-gray-8">{{ __("Items") }}</div>
				<ArrayEditor :arr :itemType :targetRatio @update:arr="updateModelValue" />
			</div>
		</template>
	</Popover>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { Popover } from "frappe-ui";
import { computed } from "vue";
import ArrayEditor from "./ArrayEditor.vue";

const props = defineProps<{
	modelValue?: string;
	itemType?: "string" | "image";
	targetRatio?: number;
}>();

const emit = defineEmits({
	"update:modelValue": (value: string) => true,
});

const arr = computed<ArrayPropItem[]>(() => {
	try {
		const parsed = JSON.parse(props.modelValue || "[]");
		return Array.isArray(parsed) ? parsed : [];
	} catch {
		return [];
	}
});

const updateModelValue = (value: ArrayPropItem[]) => {
	emit("update:modelValue", JSON.stringify(value));
};
</script>
