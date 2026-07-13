<template>
	<!-- final step: full-page template selector -->
	<div v-if="step === 'templates'" class="flex h-screen flex-col bg-surface-base">
		<div class="mx-auto w-full max-w-3xl px-8 pt-16">
			<img src="/builder_logo.png" alt="Builder" class="h-8" />
		</div>
		<div class="flex-1 overflow-hidden">
			<TemplateGallery
				class="mx-auto h-full w-full max-w-3xl"
				:max-groups="8"
				:heading="templateHeading"
				subtitle="Choose a template to get a head start, or start from scratch." />
		</div>
	</div>

	<!-- question steps: one question per page -->
	<div v-else class="flex h-screen flex-col items-center overflow-y-auto p-5">
		<!-- top-anchored (not centered) so the logo/heading never move between steps
		     or when the "Other" textarea expands -->
		<div class="mt-[28vh] flex w-full max-w-sm flex-col gap-5">
			<img src="/builder_logo.png" alt="Builder" class="h-8 self-start" />
			<div class="relative flex flex-col gap-1.5">
				<!-- kept mounted (invisible on step 1) so nothing shifts when it appears -->
				<Button
					variant="ghost"
					class="absolute -left-11 top-0"
					:class="{ invisible: isFirst }"
					label="Back"
					@click="goBack">
					<template #icon>
						<LucideChevronLeft class="size-4" />
					</template>
				</Button>
				<h1 class="text-2xl font-bold text-ink-gray-9">{{ activeQuestion.heading }}</h1>
				<p class="text-base text-ink-gray-6">{{ activeQuestion.subtitle }}</p>
			</div>

			<div class="flex flex-wrap gap-3.5">
				<Button
					v-for="opt in activeQuestion.options"
					:key="opt.value"
					:variant="answers[activeQuestion.key] === opt.value ? 'subtle' : 'outline'"
					:label="opt.label"
					:class="{ 'border border-transparent': answers[activeQuestion.key] === opt.value }"
					@click="select(opt.value)" />
			</div>

			<!-- free-text detail, revealed when "Other" is picked. -mt-5 cancels the
			     column gap while collapsed (the inner mt-5 restores it when open) so
			     the closed state doesn't leave a double gap before Next. The inner
			     translate makes the whole textarea slide down from under the pills
			     (drawer-style) instead of being clipped mid-reveal. -->
			<div
				class="-mt-5 grid transition-[grid-template-rows,opacity] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]"
				:class="isOtherSelected ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'">
				<div class="overflow-hidden">
					<div
						class="transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]"
						:class="isOtherSelected ? 'translate-y-0' : '-translate-y-full'">
						<Textarea
							ref="otherInput"
							v-model="otherText[activeQuestion.key]"
							class="mt-5"
							variant="subtle"
							:rows="3"
							:placeholder="activeQuestion.otherPlaceholder"
							:tabindex="isOtherSelected ? 0 : -1" />
					</div>
				</div>
			</div>

			<Button
				variant="solid"
				size="md"
				class="w-full"
				label="Next"
				:disabled="!answers[activeQuestion.key]"
				@click="goNext" />
		</div>

		<Button variant="ghost" label="Skip for now" class="fixed bottom-8" @click="skip" />
	</div>
</template>

<script setup lang="ts">
import TemplateGallery from "@/components/Templates/TemplateGallery.vue";
import { useDashboardState } from "@/composables/useDashboardState";
import { builderSettings } from "@/data/builderSettings";
import { sessionUser } from "@/router";
import { getUserInfo } from "@/usersInfo";
import { Button, Textarea } from "frappe-ui";
import { useTelemetry } from "frappe-ui/frappe";
import { computed, nextTick, reactive, ref } from "vue";
import LucideChevronLeft from "~icons/lucide/chevron-left";

// Pulse is event-only (no person properties), but every event carries the
// (anonymized, stable) user id, so this single event can be joined to the
// rest of the user's funnel for persona-wise segmentation.
const telemetry = useTelemetry();
const { templateCategoryFilter } = useDashboardState();
// Dev benches have telemetry off; ?persona_survey=test logs the payload instead.
const devForceShow = new URLSearchParams(window.location.search).get("persona_survey") === "test";

type QuestionKey = "use_case" | "role" | "source";

const questions: {
	key: QuestionKey;
	heading: string;
	subtitle: string;
	otherPlaceholder: string;
	options: { value: string; label: string }[];
}[] = [
	{
		key: "source",
		heading: "How did you hear about Builder?",
		subtitle: "Just curious, it helps us know what's working.",
		otherPlaceholder: "I heard from the community",
		options: [
			{ value: "search", label: "Search (Google)" },
			{ value: "youtube", label: "YouTube" },
			{ value: "friend", label: "Friend / colleague" },
			{ value: "frappe_ecosystem", label: "Frappe / ERPNext" },
			{ value: "social", label: "Social media" },
			{ value: "other", label: "Other" },
		],
	},
	{
		key: "role",
		heading: "Which one best describes you?",
		subtitle: "This helps us personalise your Builder experience",
		otherPlaceholder: "I'm a student building my first site",
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
		heading: "What do you want to build first?",
		subtitle: "We'll point you to the right starting templates",
		otherPlaceholder: "A booking site for my clinic",
		options: [
			{ value: "marketing_site", label: "Marketing / landing site" },
			{ value: "ecommerce", label: "Online store / E-commerce" },
			{ value: "portfolio", label: "Portfolio / personal site" },
			{ value: "web_app_ui", label: "Web app UI" },
			{ value: "internal_tool", label: "Internal tool / dashboard" },
			{ value: "exploring", label: "Just exploring" },
			{ value: "other", label: "Other" },
		],
	},
];

const answers = reactive<Record<QuestionKey, string | undefined>>({
	use_case: undefined,
	role: undefined,
	source: undefined,
});
const otherText = reactive<Record<QuestionKey, string>>({
	use_case: "",
	role: "",
	source: "",
});

// question steps followed by the full-page template selector
const stepOrder = [...questions.map((q) => q.key), "templates"] as const;
const stepIndex = ref(0);
const step = computed(() => stepOrder[stepIndex.value]);
const isFirst = computed(() => stepIndex.value === 0);
const activeQuestion = computed(() => questions.find((q) => q.key === step.value)!);
const isOtherSelected = computed(() => answers[activeQuestion.value.key] === "other");

const otherInput = ref<InstanceType<typeof Textarea>>();

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

// surface the templates that match what the user said they want to build:
// seeds the gallery's persisted category filter (used by the templates dialog too)
const useCaseToCategory: Record<string, string> = {
	marketing_site: "Marketing",
	ecommerce: "E-commerce",
	portfolio: "Portfolio",
};

function select(value: string) {
	// only highlight the choice; advancing is a deliberate Next click so a
	// stray double-click can't skip past the following question
	answers[activeQuestion.value.key] = value;
	// preventScroll: focusing the still-clipped textarea mid-animation would
	// otherwise scroll-jump the page
	if (value === "other") nextTick(() => otherInput.value?.el?.focus({ preventScroll: true }));
}

function goBack() {
	stepIndex.value = Math.max(0, stepIndex.value - 1);
}

function goNext() {
	const next = stepIndex.value + 1;
	// entering the template step means the questions are done, persist + capture now
	// so any exit from the selector (template, blank, or skip) won't re-trigger the survey.
	if (stepOrder[next] === "templates") finishQuestions();
	stepIndex.value = next;
}

function skip() {
	finishQuestions(true);
	stepIndex.value = stepOrder.indexOf("templates");
}

let submitted = false;
function finishQuestions(skipped = false) {
	if (submitted) return;
	submitted = true;
	const category = answers.use_case && useCaseToCategory[answers.use_case];
	if (category) templateCategoryFilter.value = category;
	// Optimistically flag done so the dashboard's redirect guard sees it before the async save lands.
	// Never let a failed save/capture block the user from moving on.
	try {
		if (builderSettings.doc) builderSettings.doc.persona_survey_done = 1;
		builderSettings.setValue.submit({ persona_survey_done: 1 });
	} catch (e) {
		console.error("[persona-survey] failed to persist", e);
	}

	const props = {
		role: answers.role || null,
		use_case: answers.use_case || null,
		source: answers.source || null,
		role_other: (answers.role === "other" && otherText.role.trim()) || null,
		use_case_other: (answers.use_case === "other" && otherText.use_case.trim()) || null,
		source_other: (answers.source === "other" && otherText.source.trim()) || null,
		skipped,
	};
	if (devForceShow) console.log("[persona-survey] capture", props);
	try {
		telemetry.capture("builder_persona_submitted", props);
	} catch (e) {
		console.error("[persona-survey] failed to capture", e);
	}
}
</script>
