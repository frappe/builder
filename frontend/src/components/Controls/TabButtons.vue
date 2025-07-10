<template>
	<RadioGroup :modelValue="value" @update:modelValue="emit('update:modelValue', $event)">
		<div class="box-border flex space-x-1 rounded bg-surface-gray-2 p-0.5 text-sm">
			<RadioGroupOption
				as="template"
				v-for="button in buttons"
				:key="button.label"
				:value="button.value ?? button.label"
				v-slot="{ active, checked }">
				<button
					:class="[
						active ? 'ring-outline-gray-2 focus-visible:ring' : '',
						!modelValue && checked ? 'border border-dashed border-outline-gray-3' : '',
						modelValue && checked ? 'bg-surface-white text-ink-gray-9 shadow' : 'text-ink-gray-7',
						'flex flex-1 justify-center gap-2 whitespace-nowrap rounded-[7px] px-3 py-[5px] leading-none transition-colors focus:outline-none',
					]">
					<FeatherIcon
						class="h-4 w-4"
						v-if="button.icon"
						:name="button.icon"
						:label="button.label"
						:aria-label="button.label" />
					<RadioGroupLabel as="span" class="flex h-4 items-center" v-show="button.label && !button.hideLabel">
						{{ button.label }}
					</RadioGroupLabel>
				</button>
			</RadioGroupOption>
		</div>
	</RadioGroup>
</template>

<script lang="ts" setup>
import { RadioGroup, RadioGroupLabel, RadioGroupOption } from "@headlessui/vue";
import { FeatherIcon } from "frappe-ui";
import { computed } from "vue";

interface Button {
	label: string;
	value?: string | number | boolean;
	icon?: string;
	hideLabel?: boolean;
}

const props = defineProps<{
	buttons: Button[];
	modelValue?: string | number | boolean;
	defaultValue?: string | number;
}>();

const value = computed(() => {
	return props.modelValue || props.defaultValue;
});

const emit = defineEmits<{
	(e: "update:modelValue", value: string | number | boolean): void;
}>();
</script>
