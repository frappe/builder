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
		<InputLabel
			class="truncate"
			:class="{ 'cursor-ns-resize': enableSlider }"
			@mousedown="$emit('mousedown', $event)">
			{{ label }}
		</InputLabel>
	</div>
</template>

<script lang="ts" setup>
import InputLabel from "@/components/Controls/InputLabel.vue";
import { Dropdown, FeatherIcon } from "frappe-ui";
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

const dropdownTrigger = ref<typeof FeatherIcon | null>(null);

defineExpose({ dropdownTrigger });
</script>
