<template>
	<form class="flex flex-col gap-5" @submit.prevent="save">
		<Password v-model="password" size="md" :description="hint" autocomplete="new-password" autofocus>
			<template #label>
				<span class="flex justify-between gap-2">
					{{ __("Password") }}
					<span v-if="level">
						{{ __("Strength:") }}
						<span class="font-medium" :class="level.color">{{ level.label }}</span>
					</span>
				</span>
			</template>
		</Password>
		<Password
			v-model="confirmation"
			size="md"
			:label="__('Confirm password')"
			:error="isMismatch ? __('Passwords do not match') : ''"
			autocomplete="new-password" />
		<ErrorMessage :message="error" />
		<Button
			type="submit"
			variant="solid"
			size="md"
			class="w-full"
			:label="__('Set password')"
			:loading="saving"
			:disabled="!password || password !== confirmation" />
	</form>
</template>

<script setup lang="ts">
import { serverMessage } from "@/composables/useSiteClone";
import { __ } from "@/translation";
import { watchDebounced } from "@vueuse/core";
import { Button, call, ErrorMessage, Password } from "frappe-ui";
import { computed, ref } from "vue";

type Strength = { score: number; feedback: { warning: string; suggestions: string[] } };

// the labels and colors of Frappe's update-password page
const levels = [
	{ label: __("Poor"), color: "text-ink-red-8" },
	{ label: __("Poor"), color: "text-ink-red-8" },
	{ label: __("Average"), color: "text-ink-amber-8" },
	{ label: __("Good"), color: "text-ink-blue-8" },
	{ label: __("Great"), color: "text-ink-green-8" },
];

const emit = defineEmits<{ done: [] }>();
const password = ref("");
const confirmation = ref("");
const strength = ref<Strength | null>(null);
const saving = ref(false);
const error = ref("");

const level = computed(() => strength.value && levels[strength.value.score]);
// Frappe gives feedback only while the score is under the site's minimum
const hint = computed(() => {
	const feedback = strength.value?.feedback;
	return feedback ? feedback.warning || feedback.suggestions.join(" ") : "";
});
const isMismatch = computed(() => Boolean(confirmation.value) && password.value !== confirmation.value);

// Frappe's own check: it scores against the user's name and email, and returns nothing when the password policy is off
watchDebounced(
	password,
	async (value) => {
		if (!value) return (strength.value = null);
		const result = await call("frappe.core.doctype.user.user.test_password_strength", {
			new_password: value,
		}).catch((e: unknown) => console.error("[onboarding] could not check the password strength", e));
		if (value === password.value) strength.value = result?.feedback ? result : null;
	},
	{ debounce: 300 },
);

async function save() {
	saving.value = true;
	error.value = "";
	try {
		await call("builder.account_onboarding.set_password", { new_password: password.value });
		window.is_password_needed = false;
		emit("done");
	} catch (e) {
		error.value = serverMessage(e, __("Couldn't set your password. Try again in a moment."));
	} finally {
		saving.value = false;
	}
}
</script>
