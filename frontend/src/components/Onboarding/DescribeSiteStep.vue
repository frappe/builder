<template>
	<form class="flex flex-col gap-5" @submit.prevent="submit">
		<Textarea
			v-model="description"
			size="md"
			variant="subtle"
			:rows="4"
			:maxlength="DESCRIPTION_MAX_LENGTH"
			:placeholder="placeholder"
			autofocus
			@keydown.enter.exact="onEnter" />
		<ErrorMessage :message="error" />
		<Button
			type="submit"
			variant="solid"
			size="md"
			class="w-full"
			:label="__('Start building')"
			:loading="starting"
			:disabled="!description.trim()" />
	</form>
</template>

<script setup lang="ts">
import { DESCRIPTION_MAX_LENGTH } from "@/composables/useAIStart";
import { __ } from "@/translation";
import { Button, ErrorMessage, Textarea } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{ useCase?: string; starting: boolean; error: string }>();
const description = defineModel<string>({ required: true });
const emit = defineEmits<{ start: [] }>();

// each names the business, says what it is, how it should feel and one thing it needs: what Bob builds best from
const examples: Record<string, string> = {
	marketing_site: __(
		"A landing page for Tidy, an app that plans your week. Friendly and bright, with a sign-up form.",
	),
	ecommerce: __(
		"A shop for Mitti, handmade clay planters from Jaipur. Earthy colours and big product photos.",
	),
	portfolio: __(
		"A portfolio for Aria Sen, a portrait photographer in Mumbai. Dark and image-first, with a booking form.",
	),
	web_app_ui: __(
		"The home screen of Ledger, a budgeting app: this month's spending, goals and recent payments.",
	),
	internal_tool: __(
		"A dashboard for a small clinic: today's appointments, who's waiting, and a patient search.",
	),
};
// for "just exploring", "other" or a skipped survey
const anyExample = __(
	"A website for Forno, a wood-fired pizzeria in Goa. Warm and rustic, with the menu and opening hours.",
);
const placeholder = computed(() => (props.useCase && examples[props.useCase]) || anyExample);

function submit() {
	if (description.value.trim() && !props.starting) emit("start");
}

// Enter sends, as in Bob's composer; Shift+Enter still breaks the line
function onEnter(event: KeyboardEvent) {
	if (event.isComposing) return;
	event.preventDefault();
	submit();
}
</script>
