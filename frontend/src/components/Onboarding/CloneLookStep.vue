<template>
	<div class="flex flex-col gap-5">
		<div class="flex flex-col gap-2.5" role="radiogroup">
			<OnboardingChoice
				v-for="option in looks"
				:key="option.value"
				:title="option.label"
				:description="option.description"
				:selected="look === option.value"
				@click="look = option.value" />
		</div>
		<ErrorMessage :message="error" />
		<Button
			variant="solid"
			size="md"
			class="w-full"
			:label="__('Start cloning')"
			:loading="starting"
			@click="emit('start')" />
	</div>
</template>

<script setup lang="ts">
import type { CloneLook } from "@/composables/useSiteClone";
import { __ } from "@/translation";
import { Button, ErrorMessage } from "frappe-ui";
import OnboardingChoice from "./OnboardingChoice.vue";

defineProps<{ starting: boolean; error: string }>();
const look = defineModel<CloneLook>({ required: true });
const emit = defineEmits<{ start: [] }>();

const looks: { value: CloneLook; label: string; description: string }[] = [
	{
		value: "clean_up",
		label: __("Clean it up"),
		description: __("Your design, tidied, and made to work well on phones."),
	},
	{ value: "as_is", label: __("As it is"), description: __("A faithful copy of how your site looks today.") },
	{
		value: "redesign",
		label: __("Redesign"),
		description: __("Your pages and words in a fresh, modern design."),
	},
];
</script>
