<template>
	<!-- final step: full-page template selector -->
	<div v-if="step === 'templates'" class="flex h-screen flex-col bg-surface-base">
		<div class="mx-auto w-full max-w-3xl px-8 pt-16">
			<img src="/builder_logo.png" alt="Builder" class="h-8" />
		</div>
		<div class="flex-1 overflow-hidden">
			<TemplateGallery
				class="h-full"
				content-class="max-w-3xl"
				blank-label="Start from scratch"
				:max-groups="8"
				:heading="templateHeading"
				subtitle="Choose a template to get a head start, or start from scratch. You can always change direction later." />
		</div>
	</div>

	<!-- question steps: one question per page -->
	<div v-else class="flex h-screen items-center justify-center p-5">
		<div class="flex w-full max-w-xl flex-col gap-8">
			<div class="flex flex-col gap-6">
				<img src="/builder_logo.png" alt="Builder" class="h-8 self-start" />
				<div class="flex flex-col gap-2">
					<h1 class="text-2xl font-semibold text-ink-gray-9">{{ activeQuestion.heading }}</h1>
				</div>
			</div>

			<div class="grid grid-cols-2 gap-3">
				<button
					v-for="opt in activeQuestion.options"
					:key="opt.value"
					class="flex items-center rounded-lg border p-4 text-left text-base transition-colors duration-150"
					:class="
						answers[activeQuestion.key] === opt.value
							? 'border-outline-gray-4 bg-surface-gray-2 text-ink-gray-9'
							: 'border-outline-gray-2 text-ink-gray-7 hover:border-outline-gray-3 hover:bg-surface-gray-1'
					"
					@click="select(opt.value)">
					{{ opt.label }}
				</button>
			</div>

			<div class="flex items-center justify-between">
				<!-- kept mounted (invisible on step 1) so the footer height stays fixed and the block doesn't shift -->
				<Button variant="ghost" icon-left="lucide-arrow-left" :class="{ invisible: isFirst }" @click="goBack">
					Back
				</Button>
				<span class="text-xs text-ink-gray-4">Step {{ stepIndex + 1 }} of {{ totalSteps }}</span>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import TemplateGallery from "@/components/Templates/TemplateGallery.vue";
import { builderSettings } from "@/data/builderSettings";
import { sessionUser } from "@/router";
import { getUserInfo } from "@/usersInfo";
import { Button } from "frappe-ui";
import { useTelemetry } from "frappe-ui/frappe";
import { computed, reactive, ref } from "vue";

// Pulse is event-only (no person properties), but every event carries the
// (anonymized, stable) user id, so this single event can be joined to the
// rest of the user's funnel for persona-wise segmentation.
const telemetry = useTelemetry();
// Dev benches have telemetry off; ?persona_survey=test logs the payload instead.
const devForceShow = new URLSearchParams(window.location.search).get("persona_survey") === "test";

type QuestionKey = "use_case" | "role" | "source";

const questions: {
	key: QuestionKey;
	heading: string;
	options: { value: string; label: string }[];
}[] = [
	{
		key: "use_case",
		heading: "What do you want to build first?",
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
		heading: "Which one best describes you?",
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
		heading: "How did you hear about Builder?",
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
	use_case: undefined,
	role: undefined,
	source: undefined,
});

// question steps followed by the full-page template selector
const stepOrder = [...questions.map((q) => q.key), "templates"] as const;
const totalSteps = stepOrder.length;
const stepIndex = ref(0);
const step = computed(() => stepOrder[stepIndex.value]);
const isFirst = computed(() => stepIndex.value === 0);
const activeQuestion = computed(() => questions.find((q) => q.key === step.value)!);

// personal greeting; fullname is an email until the fetch lands (skip it then)
const userInfo = getUserInfo(sessionUser.value);
const greetingName = computed(() => {
	const fullname = userInfo?.fullname;
	// skip the name until it resolves, or when it's an email / the Guest fallback
	if (!fullname || fullname.includes("@") || fullname === "Guest") return "";
	return `, ${fullname.split(" ")[0]}`;
});
const templateHeading = computed(() =>
	greetingName.value ? `You're all set${greetingName.value}. Pick a starting point` : "Pick a starting point",
);

function select(value: string) {
	// one click answers the question and moves on — no separate Continue step
	answers[activeQuestion.value.key] = value;
	goNext();
}

function goBack() {
	stepIndex.value = Math.max(0, stepIndex.value - 1);
}

function goNext() {
	const next = stepIndex.value + 1;
	// entering the template step means the questions are done — persist + capture now
	// so any exit from the selector (template, blank, or skip) won't re-trigger the survey.
	if (stepOrder[next] === "templates") finishQuestions();
	stepIndex.value = next;
}

let submitted = false;
function finishQuestions() {
	if (submitted) return;
	submitted = true;
	// Optimistically flag done so the dashboard's redirect guard sees it before the async save lands.
	if (builderSettings.doc) builderSettings.doc.persona_survey_done = 1;
	builderSettings.setValue.submit({ persona_survey_done: 1 });

	const props = {
		role: answers.role || null,
		use_case: answers.use_case || null,
		source: answers.source || null,
	};
	if (devForceShow) console.log("[persona-survey] capture", props);
	telemetry.capture("builder_persona_submitted", props);
}
</script>
