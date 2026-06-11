<template>
	<Dialog v-model="show" title="Help us tailor Builder to you" size="lg">
		<template #body-content>
			<p class="mb-5 text-p-sm text-ink-gray-6">
				A few quick questions so we can point you at the right templates and guides. Optional, takes 15
				seconds.
			</p>
			<div class="flex flex-col gap-6">
				<div v-for="q in questions" :key="q.key" class="flex flex-col gap-2">
					<InputLabel>{{ q.label }}</InputLabel>
					<div class="flex flex-wrap gap-2">
						<button
							v-for="opt in q.options"
							:key="opt.value"
							type="button"
							class="rounded-md border px-3 py-1.5 text-p-sm transition-colors"
							:class="
								answers[q.key] === opt.value
									? 'border-outline-gray-4 bg-surface-gray-3 text-ink-gray-9'
									: 'border-outline-gray-2 text-ink-gray-7 hover:bg-surface-gray-2'
							"
							@click="select(q.key, opt.value)">
							{{ opt.label }}
						</button>
					</div>
				</div>
			</div>
		</template>
		<template #actions>
			<div class="flex justify-between">
				<Button variant="ghost" @click="dismiss">Skip</Button>
				<Button variant="solid" :disabled="!hasAnyAnswer" @click="submit">Submit</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import { builderSettings } from "@/data/builderSettings";
import { sessionUser } from "@/router";
import { Button, Dialog } from "frappe-ui";
import { useTelemetry } from "frappe-ui/frappe";
import { computed, reactive, ref, watch } from "vue";

// Pulse is event-only (no person properties), but every event carries the
// (anonymized, stable) user id, so this single event can be joined to the
// rest of the user's funnel for persona-wise segmentation.
// Keep the reactive object (don't destructure) so `isEnabled` stays reactive —
// it resolves asynchronously after the plugin's is_enabled() call returns.
const telemetry = useTelemetry();

// TEMP (local testing): telemetry — and therefore this survey — is disabled on
// dev benches (Pulse requires FrappeCloud). To exercise the flow locally, open
// the dashboard with `?persona_survey=test`; that forces the survey to show and
// logs the payload that would be sent. Remove this block before shipping.
const devForceShow = new URLSearchParams(window.location.search).get("persona_survey") === "test2";

type QuestionKey = "role" | "use_case" | "source";

const questions: { key: QuestionKey; label: string; options: { value: string; label: string }[] }[] = [
	{
		key: "role",
		label: "Which best describes you?",
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
		key: "use_case",
		label: "What do you want to build first?",
		options: [
			{ value: "marketing_site", label: "Marketing / landing site" },
			{ value: "web_app_ui", label: "Web app UI" },
			{ value: "internal_tool", label: "Internal tool" },
			{ value: "portfolio", label: "Portfolio / personal site" },
			{ value: "client_work", label: "Client work" },
			{ value: "exploring", label: "Just exploring" },
		],
	},
	{
		key: "source",
		label: "How did you hear about Builder?",
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

const show = ref(false);
const answers = reactive<Record<QuestionKey, string | null>>({
	role: null,
	use_case: null,
	source: null,
});

const hasAnyAnswer = computed(() => Object.values(answers).some(Boolean));

function select(key: QuestionKey, value: string) {
	answers[key] = answers[key] === value ? null : value;
}

function markDone() {
	// Site-wide flag (Builder Settings is a Single). Acceptable show-once proxy
	// for single-user trial sites; revisit if Builder gains multi-user trials.
	builderSettings.setValue.submit({ persona_survey_done: 1 });
}

function track(event: string, props: Record<string, any> = {}) {
	// In dev, capture() is a no-op (telemetry off) — log so the flow is observable.
	if (devForceShow) console.log("[persona-survey] capture", event, props);
	telemetry.capture(event, props);
}

function submit() {
	track("builder_persona_submitted", {
		role: answers.role,
		use_case: answers.use_case,
		source: answers.source,
	});
	markDone();
	show.value = false;
}

function dismiss() {
	track("builder_persona_skipped");
	markDone();
	show.value = false;
}

// Only ask once telemetry is confirmed on (capture is a no-op otherwise — no
// point surfacing a survey we can't record) and the survey hasn't run yet.
watch(
	[() => telemetry.isEnabled, () => builderSettings.doc, sessionUser],
	() => {
		if (!telemetry.isEnabled && !devForceShow) return;
		if (!builderSettings.doc) return;
		// devForceShow ignores the show-once flag so the flow can be re-run on reload
		if (builderSettings.doc.persona_survey_done && !devForceShow) return;
		if (!sessionUser.value || sessionUser.value === "Guest") return;
		// small delay so the dashboard settles before the modal appears
		setTimeout(() => {
			if (devForceShow || !builderSettings.doc?.persona_survey_done) show.value = true;
		}, 1500);
	},
	{ immediate: true },
);
</script>
