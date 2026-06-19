<template>
	<div class="flex h-screen items-center justify-center p-5">
		<div class="flex w-full max-w-lg flex-col gap-6 rounded-lg bg-surface-base p-8">
			<img src="/builder_logo.png" alt="Builder" class="h-8 self-start" />
			<div class="flex flex-col gap-1">
				<h1 class="text-xl font-semibold text-ink-gray-9">Before we start</h1>
				<p class="text-p-sm text-ink-gray-6">
					Answer a few quick questions so we can improve your Builder experience.
				</p>
			</div>
			<div class="flex flex-col gap-5">
				<div v-for="q in questions" :key="q.key" class="flex flex-col gap-2">
					<Select
						v-model="answers[q.key]"
						:label="q.label"
						:placeholder="q.placeholder"
						:options="q.options" />
				</div>
			</div>
			<div class="flex justify-end">
				<Button variant="solid" :disabled="!hasAnyAnswer" @click="submit">Submit</Button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { builderSettings } from "@/data/builderSettings";
import router from "@/router";
import { Button, Select } from "frappe-ui";
import { useTelemetry } from "frappe-ui/frappe";
import { computed, reactive } from "vue";

// Pulse is event-only (no person properties), but every event carries the
// (anonymized, stable) user id, so this single event can be joined to the
// rest of the user's funnel for persona-wise segmentation.
const telemetry = useTelemetry();

// TEMP (local testing): telemetry is disabled on dev benches (Pulse requires
// FrappeCloud), so capture() is a no-op there. Append `?persona_survey=test2`
// when navigating here to log the payload that would be sent. Remove before shipping.
const devForceShow = new URLSearchParams(window.location.search).get("persona_survey") === "test2";

type QuestionKey = "role" | "use_case" | "source";

const questions: {
	key: QuestionKey;
	label: string;
	placeholder: string;
	options: { value: string; label: string }[];
}[] = [
	{
		key: "use_case",
		label: "What do you want to build first?",
		placeholder: "Pick what you'll build",
		options: [
			{ value: "marketing_site", label: "Marketing / landing site" },
			{ value: "web_app_ui", label: "Web app UI" },
			{ value: "internal_tool", label: "Internal tool" },
			{ value: "dashboard", label: "Dashboard / admin panel" },
			{ value: "portfolio", label: "Portfolio / personal site" },
			{ value: "exploring", label: "Just exploring" },
		],
	},
	{
		key: "role",
		label: "Which one best describes you?",
		placeholder: "Pick what fits best",
		options: [
			{ value: "designer", label: "Designer" },
			{ value: "developer", label: "Developer" },
			{ value: "founder", label: "Founder / Business owner" },
			{ value: "marketer", label: "Marketer" },
			{ value: "agency_freelancer", label: "Agency / Freelancer" },
			{ value: "other", label: "Other" },
		],
	},
	{
		key: "source",
		label: "How did you hear about Builder?",
		placeholder: "Pick where you found us",
		options: [
			{ value: "search", label: "Search (Google)" },
			{ value: "youtube", label: "YouTube" },
			{ value: "friend", label: "Friend / colleague" },
			{ value: "frappe_ecosystem", label: "Frappe / ERPNext" },
			{ value: "social", label: "Social media" },
			{ value: "other", label: "Other" },
		],
	},
];

const answers = reactive<Record<QuestionKey, string | undefined>>({
	role: undefined,
	use_case: undefined,
	source: undefined,
});

const hasAnyAnswer = computed(() => Object.values(answers).some(Boolean));

function markDone() {
	// Site-wide flag (Builder Settings is a Single). Acceptable show-once proxy
	// for single-user trial sites; revisit if Builder gains multi-user trials.
	// Update the local doc optimistically so the dashboard's redirect guard sees
	// the survey as done the moment we navigate back (the submit is async).
	if (builderSettings.doc) builderSettings.doc.persona_survey_done = 1;
	builderSettings.setValue.submit({ persona_survey_done: 1 });
}

function track(event: string, props: Record<string, any> = {}) {
	// In dev, capture() is a no-op (telemetry off) — log so the flow is observable.
	if (devForceShow) console.log("[persona-survey] capture", event, props);
	telemetry.capture(event, props);
}

function finish() {
	markDone();
	router.replace({ name: "home" });
}

function submit() {
	track("builder_persona_submitted", {
		role: answers.role || null,
		use_case: answers.use_case || null,
		source: answers.source || null,
	});
	finish();
}

function dismiss() {
	track("builder_persona_skipped");
	finish();
}
</script>
