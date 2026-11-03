<template>
	<section v-if="isCloudBillingAvailable" class="flex flex-col gap-3 rounded-lg border border-outline-gray-2 p-5">
		<div class="flex flex-col gap-1">
			<h2 class="text-lg font-semibold text-ink-gray-9">{{ heading }}</h2>
			<p class="text-p-base text-ink-gray-6">{{ subtitle }}</p>
		</div>

		<form v-if="!clone || failed" class="flex flex-col gap-3" @submit.prevent="start">
			<TextInput v-model="url" type="url" size="md" :placeholder="__('yourbusiness.com')" required />
			<div class="flex flex-wrap gap-2">
				<Button
					v-for="option in looks"
					:key="option.value"
					type="button"
					:variant="look === option.value ? 'subtle' : 'outline'"
					:label="option.label"
					@click="look = option.value" />
			</div>
			<p class="text-p-sm text-ink-gray-5">{{ looks.find((o) => o.value === look)?.hint }}</p>
			<ErrorMessage :message="error" />
			<div>
				<Button type="submit" variant="solid" :loading="starting" :label="failed ? __('Try again') : __('Clone my site')" />
			</div>
		</form>

		<div v-else class="flex flex-col gap-3">
			<div class="flex items-center gap-2 text-base text-ink-gray-8">
				<LoadingIndicator v-if="!done" class="size-4 text-ink-gray-6" />
				<span class="font-medium">{{ host }}</span>
				<span class="text-ink-gray-5">{{ latest }}</span>
			</div>
			<p v-if="!done" class="text-p-sm text-ink-gray-5">
				{{ __("This takes about fifteen minutes. You can explore Builder meanwhile and come back here.") }}
			</p>
			<div v-else class="flex gap-2">
				<Button variant="solid" :label="__('Open my pages')" @click="router.push({ name: 'home' })" />
				<Button variant="outline" :label="__('View the site')" link="/" />
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import { isCloudBillingAvailable, useCloudBilling } from "@/composables/useCloudBilling";
import router from "@/router";
import { __ } from "@/translation";
import { Button, ErrorMessage, LoadingIndicator, TextInput, call } from "frappe-ui";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

type CloneView = {
	status: string;
	source_url: string;
	events?: { text: string }[];
	error?: string;
};

const POLL_MS = 5000;
const looks = [
	{ value: "clean_up", label: __("Clean it up"), hint: __("Your design, tidied up and made to work well on phones.") },
	{ value: "as_is", label: __("As it is"), hint: __("A faithful copy of your current design.") },
	{ value: "redesign", label: __("Redesign"), hint: __("Your pages and words in a fresh, modern design.") },
];

useCloudBilling();
const url = ref("");
const look = ref("clean_up");
const clone = ref<CloneView | null>(null);
const starting = ref(false);
const error = ref("");
let timer: ReturnType<typeof setTimeout> | undefined;

const done = computed(() => clone.value?.status === "Done");
const failed = computed(() => ["Failed", "Expired"].includes(clone.value?.status ?? ""));
const host = computed(() => (clone.value ? new URL(clone.value.source_url).host : ""));
const latest = computed(() => (done.value ? __("is ready") : clone.value?.events?.at(-1)?.text ?? __("Starting…")));
const heading = computed(() => (done.value ? __("Your site is cloned") : __("Have a website already?")));
const subtitle = computed(() =>
	done.value
		? __("Its pages, text and images are in Builder now, ready to edit.")
		: __("Clone it into Builder: your pages, text and images, in the look you pick."),
);

async function start() {
	starting.value = true;
	error.value = "";
	try {
		clone.value = await call("builder.clone_onboarding.start_clone", { url: url.value, look: look.value });
		poll();
	} catch (e) {
		error.value = (e as Error).message;
	} finally {
		starting.value = false;
	}
}

async function poll() {
	clearTimeout(timer);
	clone.value = await call("builder.clone_onboarding.clone_status").catch(() => clone.value);
	if (failed.value) error.value = clone.value?.error || __("The clone didn't finish. Try again.");
	else if (clone.value && !done.value) timer = setTimeout(poll, POLL_MS);
}

// a clone started earlier keeps going on the server, so pick its progress back up
onMounted(poll);
onBeforeUnmount(() => clearTimeout(timer));
</script>
