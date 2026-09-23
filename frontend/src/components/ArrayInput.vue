<template>
	<Popover :offset="20" side="left" align="center" bare>
		<template #trigger>
			<div class="relative flex w-full gap-2">
				<div v-if="label" class="flex w-1/3 min-w-[88px] shrink-0 items-center">
					<InputLabel class="w-full truncate">
						{{ label }}
					</InputLabel>
				</div>
				<Button variant="subtle" class="group w-full min-w-0 !justify-start !text-sm">
					<template #prefix>
						<div v-if="thumbnails.length" class="flex shrink-0 -space-x-1.5">
							<img
								v-for="(url, index) in thumbnails"
								:key="index"
								:src="url"
								alt=""
								class="size-4 rounded-4 object-cover ring-1 ring-surface-gray-2 group-hover:ring-surface-gray-3" />
						</div>
					</template>
					<span :class="arr.length ? 'text-ink-gray-8' : 'text-ink-gray-4'">
						{{ countLabel }}
					</span>
					<template #suffix>
						<span
							class="lucide-pencil ml-auto mr-1 size-3.5 shrink-0 text-ink-gray-7 group-hover:text-ink-gray-8" />
					</template>
				</Button>
			</div>
		</template>
		<template #default>
			<div
				@click.stop
				@mousedown.stop
				class="flex flex-col gap-3 rounded-6 bg-surface-base p-4 shadow-lg"
				:class="itemType === 'image' ? 'w-72' : 'w-60'">
				<div class="shrink-0 text-sm text-ink-gray-8">{{ __("Items") }}</div>
				<ArrayEditor listClass="max-h-[180px]" :arr :itemType :targetRatio @update:arr="updateModelValue" />
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

const thumbnails = computed(() => {
	if (props.itemType !== "image") return [];
	return arr.value
		.map((item) => (typeof item === "string" ? item : item.url))
		.filter(Boolean)
		.slice(0, 3);
});

const countLabel = computed(() => {
	const count = arr.value.length;
	if (!count) return __("Add items");
	return count === 1 ? __("1 item") : __("{0} items", [count]);
});

const updateModelValue = (value: ArrayPropItem[]) => {
	emit("update:modelValue", JSON.stringify(value));
};
</script>
