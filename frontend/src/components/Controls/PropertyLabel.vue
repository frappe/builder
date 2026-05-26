<template>
	<div class="flex items-center gap-2" :class="containerClass">
		<Dropdown v-if="showDropdown" size="sm" :options="dropdownOptions">
			<template v-slot="{ open }">
				<span
					ref="dropdownTrigger"
					class="lucide-plus-circle h-3 w-3 cursor-pointer text-ink-gray-7 hover:text-ink-gray-9"
					aria-hidden="true"
					@click="open" />
			</template>
		</Dropdown>
		<InputLabel
			class="truncate"
			:title="label"
			:class="{ 'cursor-ns-resize': enableSlider }"
			@mousedown="$emit('mousedown', $event)">
			{{ label }}
		</InputLabel>
	</div>
</template>

<script lang="ts" setup>
import InputLabel from "@/components/Controls/InputLabel.vue";
import { Dropdown } from "frappe-ui";
import { ref } from "vue";

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

const dropdownTrigger = ref<HTMLElement | null>(null);

defineExpose({ dropdownTrigger });
</script>
