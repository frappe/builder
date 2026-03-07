<template>
	<div class="flex items-center gap-2" :class="containerClass">
		<Dropdown v-if="showDropdown" size="sm" :options="dropdownOptions">
			<template v-slot="{ open }">
				<FeatherIcon
					ref="dropdownTrigger"
					name="plus-circle"
					class="h-3 w-3 cursor-pointer text-ink-gray-7 hover:text-ink-gray-9"
					@click="open" />
			</template>
		</Dropdown>
		<Tooltip :disabled="!isTruncated" :text="label" placement="bottom">
			<InputLabel
				ref="labelRef"
				class="truncate"
				:class="{ 'cursor-ns-resize': enableSlider }"
				@mousedown="$emit('mousedown', $event)">
				{{ label }}
			</InputLabel>
		</Tooltip>
	</div>
</template>

<script lang="ts" setup>
import InputLabel from "@/components/Controls/InputLabel.vue";
import { useResizeObserver } from "@vueuse/core";
import { Dropdown, FeatherIcon, Tooltip } from "frappe-ui";
import { ref, onMounted, nextTick } from "vue";

const props = defineProps<{
	label: string;
	showDropdown?: boolean;
	dropdownOptions?: Array<{ label: string; onClick: () => void }>;
	enableSlider?: boolean;
	containerClass?: string;
}>();

defineEmits<{
	(e: "mousedown", event: MouseEvent): void;
}>();

const dropdownTrigger = ref<typeof FeatherIcon | null>(null);
const labelRef = ref<InstanceType<typeof InputLabel> | null>(null);
const isTruncated = ref(false);

function checkTruncation() {
	if (!labelRef.value) return;
	const el = labelRef.value.$el as HTMLElement;
	if (!el) return;

	isTruncated.value = el.scrollWidth > el.clientWidth;
}

onMounted(async () => {
	await nextTick();
	checkTruncation();
});

useResizeObserver(labelRef, () => {
	checkTruncation();
});

defineExpose({ dropdownTrigger });
</script>
