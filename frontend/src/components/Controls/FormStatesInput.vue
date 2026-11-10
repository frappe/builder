<template>
	<div class="flex items-start justify-between gap-2">
		<InputLabel class="h-7 w-1/3 min-w-[88px] shrink-0" :description="description">{{ label }}</InputLabel>
		<div class="grid w-full min-w-0 grid-cols-2 gap-x-2 gap-y-1.5 py-1">
			<Checkbox
				v-for="state in formStates"
				:key="state.value"
				:label="state.label"
				:modelValue="modelValue.includes(state.value)"
				:disabled="modelValue.length === 1 && modelValue.includes(state.value)"
				@update:modelValue="(shown) => toggle(state.value, Boolean(shown))" />
		</div>
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import { formStates } from "@/utils/formStates";
import { Checkbox } from "frappe-ui";

const props = defineProps<{
	label: string;
	description?: string;
	modelValue: string[];
}>();

const emit = defineEmits<{
	"update:modelValue": [states: string[]];
}>();

const toggle = (state: string, shown: boolean) =>
	emit(
		"update:modelValue",
		shown ? [...props.modelValue, state] : props.modelValue.filter((s) => s !== state),
	);
</script>
