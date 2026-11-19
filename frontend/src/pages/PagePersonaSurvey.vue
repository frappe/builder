<template>
	<!-- template picker: full page, reached from the start step -->
	<div v-if="step === 'templates'" class="flex h-screen flex-col bg-surface-base">
		<div class="mx-auto w-full max-w-3xl px-8 pt-16">
			<div class="relative">
				<Button variant="ghost" class="absolute -left-11 top-0.5" :label="__('Back')" @click="goBack">
					<template #icon>
						<LucideChevronLeft class="size-4" />
					</template>
				</Button>
				<img src="/builder_logo.png" alt="Builder" class="h-8" />
			</div>
		</div>
		<div class="flex-1 overflow-hidden">
			<TemplateGallery
				class="mx-auto h-full w-full max-w-3xl"
				:max-groups="8"
				:heading="__('Pick a template')"
				:subtitle="__('Choose one to get a head start, or start from scratch.')" />
		</div>
	</div>

	<!-- one decision per page: the questions, then how to start -->
	<div v-else class="flex h-screen flex-col items-center overflow-y-auto p-5">
		<!-- top-anchored so the logo/heading never move between steps -->
		<div class="mt-[28vh] flex w-full max-w-sm flex-col gap-5 pb-24">
			<img src="/builder_logo.png" alt="Builder" class="h-8 self-start" />
			<div class="relative flex flex-col gap-1.5">
				<!-- kept mounted (invisible when there's nowhere to go back to) so nothing shifts when it appears -->
				<Button
					variant="ghost"
					class="absolute -left-11 top-0"
					:class="{ invisible: !canGoBack }"
					:label="__('Back')"
					@click="goBack">
					<template #icon>
						<LucideChevronLeft class="size-4" />
					</template>
				</Button>
				<h1 class="break-words text-xl font-bold text-ink-gray-9">{{ screen.heading }}</h1>
				<p class="text-base text-ink-gray-6">{{ screen.subtitle }}</p>
			</div>

			<template v-if="activeQuestion">
				<div class="flex flex-wrap gap-3.5">
					<Button
						v-for="opt in activeQuestion.options"
						:key="opt.value"
						:variant="answers[activeQuestion.key] === opt.value ? 'subtle' : 'outline'"
						:label="opt.label"
						:class="{ 'border border-transparent': answers[activeQuestion.key] === opt.value }"
						@click="select(opt.value)" />
				</div>

				<!-- "Other" free text; -mt-5 + inner mt-5 avoid a double column gap while collapsed -->
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
					:label="__('Next')"
					:disabled="!answers[activeQuestion.key]"
					@click="goNext" />
			</template>
			<PasswordStep v-else-if="step === 'password'" @done="finishPassword" />
			<!-- a site created from a description: Bob gets it at once -->
			<template v-else-if="step === 'starting'">
				<StartDescriptionCard :description="siteDescription" />
				<div class="flex items-center gap-2.5 text-p-sm text-ink-gray-7">
					<LoadingIndicator class="size-4 text-ink-gray-6" />
					{{ __("Opening a page for Bob") }}
				</div>
			</template>
			<template v-else-if="step === 'start'">
				<StartDescriptionCard
					v-if="promptStart.pending"
					:description="siteDescription"
					:notice="startNotice"
					copyable />
				<StartChoice :can-clone="canClone" :ai-start="startChoiceOffer" @choose="choose" />
			</template>
			<DescribeSiteStep
				v-else-if="step === 'describe'"
				v-model="siteDescription"
				:use-case="answers.use_case"
				:starting="describeStarting"
				:error="describeError"
				@start="startDescribing" />
			<CloneAddressStep
				v-else-if="step === 'clone-address'"
				v-model="cloneAddress"
				@next="goTo('clone-look')" />
			<CloneLookStep
				v-else-if="step === 'clone-look'"
				v-model="cloneLook"
				:starting="cloneStarting"
				:error="cloneError"
				@start="startCloning" />
			<CloneProgressStep
				v-else-if="step === 'clone-progress'"
				@open="router.push({ name: 'home' })"
				@retry="retryClone" />
		</div>

		<Button
			v-if="activeQuestion"
			variant="ghost"
			:label="__('Skip for now')"
			class="fixed bottom-8"
			@click="skip" />
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import CloneAddressStep from "@/components/Onboarding/CloneAddressStep.vue";
import CloneLookStep from "@/components/Onboarding/CloneLookStep.vue";
import CloneProgressStep from "@/components/Onboarding/CloneProgressStep.vue";
import DescribeSiteStep from "@/components/Onboarding/DescribeSiteStep.vue";
import PasswordStep from "@/components/Onboarding/PasswordStep.vue";
import StartChoice from "@/components/Onboarding/StartChoice.vue";
import StartDescriptionCard from "@/components/Onboarding/StartDescriptionCard.vue";
import TemplateGallery from "@/components/Templates/TemplateGallery.vue";
import { type AIStartOffer, useAIStart } from "@/composables/useAIStart";
import { useDashboardState } from "@/composables/useDashboardState";
import { type CloneLook, serverMessage, useSiteClone } from "@/composables/useSiteClone";
import router, { sessionUser } from "@/router";
import useBuilderStore from "@/stores/builderStore";
import { getUserInfo } from "@/usersInfo";
import { isMounted } from "@/utils/frappePage";
import { markPersonaSurveyDone, submitPersonaSurvey } from "@/utils/personaSurvey";
import { PromptStart, type PromptStartOutcome, type StartNotice } from "@/utils/promptStart";
import { Button, call, LoadingIndicator, Textarea, toast } from "frappe-ui";
import { useTelemetry } from "@framework/ui/telemetry";
import { computed, nextTick, reactive, ref } from "vue";
import LucideChevronLeft from "~icons/lucide/chevron-left";

// Every event carries the (anonymized, stable) user id, so this single event can
// be joined to the rest of the user's funnel for persona-wise segmentation. The
// answers are also attached to the site's Pulse profile (identify_persona) so
// site-level metrics split by persona without a join.
const telemetry = useTelemetry();
const { templateCategoryFilter } = useDashboardState();
// ?persona_survey=test shows the survey off Frappe Cloud and logs the payload.
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
		heading: __("How did you hear about Builder?"),
		subtitle: __("Just curious, it helps us know what's working."),
		otherPlaceholder: __("I heard from the community"),
		options: [
			{ value: "search", label: __("Search (Google)") },
			{ value: "youtube", label: __("YouTube") },
			{ value: "friend", label: __("Friend / colleague") },
			{ value: "frappe_ecosystem", label: __("Frappe / ERPNext") },
			{ value: "social", label: __("Social media") },
			{ value: "other", label: __("Other") },
		],
	},
	{
		key: "role",
		heading: __("Which one best describes you?"),
		subtitle: __("This helps us personalise your Builder experience"),
		otherPlaceholder: __("I'm a student building my first site"),
		options: [
			{ value: "designer", label: __("Designer") },
			{ value: "developer", label: __("Developer") },
			{ value: "founder", label: __("Founder / Business owner") },
			{ value: "marketer", label: __("Marketer") },
			{ value: "agency_freelancer", label: __("Agency / Freelancer") },
			{ value: "other", label: __("Other") },
		],
	},
	{
		key: "use_case",
		heading: __("What do you want to build first?"),
		subtitle: __("We'll point you to the right starting templates"),
		otherPlaceholder: __("A booking site for my clinic"),
		options: [
			{ value: "marketing_site", label: __("Marketing / landing site") },
			{ value: "ecommerce", label: __("Online store / E-commerce") },
			{ value: "portfolio", label: __("Portfolio / personal site") },
			{ value: "web_app_ui", label: __("Web app UI") },
			{ value: "internal_tool", label: __("Internal tool / dashboard") },
			{ value: "exploring", label: __("Just exploring") },
			{ value: "other", label: __("Other") },
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

type CloneStep = "clone-address" | "clone-look" | "clone-progress";
type Step = QuestionKey | "password" | "starting" | "start" | "describe" | CloneStep | "templates";
const questionKeys = questions.map((q) => q.key);
// frappe.page: a site created from a description opens with Bob building from it. The questions wait for the user's
// next visit to the dashboard: they already said what they want, and came here to watch it built.
const promptStart = new PromptStart();
// Frappe Cloud v2: a first user signed in without a password sets one before anything else
const step = ref<Step>(
	window.is_password_needed ? "password" : promptStart.pending ? "starting" : questionKeys[0]
);
const history = ref<Step[]>([]);
const activeQuestion = computed(() => questions.find((q) => q.key === step.value));
const isOtherSelected = computed(
	() => Boolean(activeQuestion.value) && answers[activeQuestion.value!.key] === "other",
);
// a started clone runs on the server, so there's no step to go back to
const canGoBack = computed(() => history.value.length > 0 && step.value !== "clone-progress");

const {
	available: canClone,
	clone,
	done: cloneDone,
	failed: cloneFailed,
	host: cloneHost,
	start,
} = useSiteClone();
const cloneAddress = ref("");
const cloneLook = ref<CloneLook>("clean_up");
const cloneStarting = ref(false);
const cloneError = ref("");

// asked on the first question, so the start step knows by the time it shows
const { offer: aiStartOffer, loaded: aiStartLoaded, start: startAI } = useAIStart();
const siteDescription = ref(promptStart.description);
const startNotice = ref<StartNotice | null>(null);
// the notice above the choices already says the allowance is spent: no second, disabled Describe saying it again
const startChoiceOffer = computed<AIStartOffer>(() =>
	startNotice.value && aiStartOffer.value.state === "spent" ? { state: "hidden" } : aiStartOffer.value,
);
const describeStarting = ref(false);
const describeError = ref("");

const otherInput = ref<InstanceType<typeof Textarea>>();

// personal greeting; fullname is an email until the fetch lands (skip it then)
const userInfo = getUserInfo(sessionUser.value);
const greetingName = computed(() => {
	const fullname = userInfo?.fullname;
	// skip the name until it resolves, or when it's an email / the Guest fallback
	if (!fullname || fullname.includes("@") || fullname === "Guest") return "";
	return `, ${fullname.split(" ")[0]}`;
});
const screen = computed(() => {
	if (activeQuestion.value)
		return { heading: activeQuestion.value.heading, subtitle: activeQuestion.value.subtitle };
	if (step.value === "password")
		return {
			heading: __("Set a password"),
			subtitle: __("You sign in as {0} with it.", [sessionUser.value]),
		};
	if (step.value === "start")
		return {
			heading: __("How would you like to start?"),
			subtitle: __("You're all set{0}. You can add pages any of these ways later too.", [greetingName.value]),
		};
	if (step.value === "starting")
		return {
			heading: __("Starting your site"),
			subtitle: __("Bob, Builder's AI, builds your first page from your description while you watch."),
		};
	if (step.value === "describe")
		return {
			heading: __("What's your website about?"),
			subtitle: __(
				"A sentence or two is enough. Bob, Builder's AI, builds your first page from it while you watch.",
			),
		};
	if (step.value === "clone-address")
		return {
			heading: __("What's your website?"),
			subtitle: __("We copy its pages, text and images into Builder. Your current site isn't touched."),
		};
	if (step.value === "clone-look")
		return {
			heading: __("How should it look?"),
			subtitle: __("Your words and images come across either way."),
		};
	return cloneScreen();
});

function cloneScreen() {
	if (cloneDone.value)
		return {
			heading: __("{0} is in Builder", [cloneHost.value]),
			subtitle: __("Its pages, text and images are ready to edit."),
		};
	if (cloneFailed.value)
		return {
			heading: __("That didn't work"),
			subtitle: clone.value?.error || __("Something went wrong on our side."),
		};
	return {
		heading: __("Cloning {0}", [cloneHost.value]),
		subtitle: __("This takes about fifteen minutes. Look around meanwhile; it keeps going."),
	};
}

// seeds the gallery's persisted category filter (used by the templates dialog too)
const useCaseToCategory: Record<string, string> = {
	marketing_site: "Marketing",
	ecommerce: "E-commerce",
	portfolio: "Portfolio",
};

function select(value: string) {
	// only highlight the choice; advancing is a deliberate Next click so a
	// stray double-click can't skip past the following question
	answers[activeQuestion.value!.key] = value;
	// preventScroll: focusing the still-clipped textarea would scroll-jump the page
	if (value === "other") nextTick(() => otherInput.value?.focus({ preventScroll: true }));
}

function goTo(next: Step) {
	history.value.push(step.value);
	step.value = next;
}

function goBack() {
	step.value = history.value.pop() ?? step.value;
}

function goNext() {
	const next = questionKeys[questionKeys.indexOf(step.value as QuestionKey) + 1];
	if (next) return goTo(next);
	// leaving the questions means they're done: persist + capture now, so any way out
	// of the start step (clone, template, blank, or closing the tab) won't re-trigger the survey
	finishQuestions();
	if (siteHasPages.value) return router.replace({ name: "home" });
	goTo("start");
}

function finishPassword() {
	if (window.persona_survey_done) return router.replace({ name: "home" });
	step.value = questionKeys[0];
}

function skip() {
	finishQuestions(true);
	if (siteHasPages.value) return router.replace({ name: "home" });
	history.value = [];
	step.value = "start";
}

// On frappe.page the questions can come after the site has pages (Bob built one from its description, then the
// user opened the dashboard): there is nothing left to start, so they end on the dashboard.
const siteHasPages = ref(false);
function checkSiteHasPages() {
	if (!isMounted) return;
	call<number>("frappe.client.get_count", { doctype: "Builder Page", filters: { is_template: 0 } })
		.then((count) => (siteHasPages.value = count > 0))
		.catch(() => {});
}
if (!promptStart.pending) checkSiteHasPages();

if (promptStart.pending) startFromDescription();

async function startFromDescription() {
	settle(await promptStart.begin(await aiStartLoaded, describe));
}

async function describe(description: string, settled?: (accepted: boolean) => void) {
	await startAI(description, settled);
	telemetry.capture("builder_describe_started", { source: promptStart.pending ? "prompt" : "onboarding" });
}

// Bob builds, or another tab of the user's does; otherwise the start step says why not, under the description
function settle(outcome: PromptStartOutcome) {
	if (outcome.kind === "started") return;
	// the other tab has Bob; this one asks the questions it owes now (home would only send it back here)
	if (outcome.kind === "elsewhere") {
		toast.info(__("Bob is building your site in another tab."));
		checkSiteHasPages();
		history.value = [];
		step.value = questionKeys[0];
		return;
	}
	startNotice.value = outcome.kind === "failed" ? failedNotice(outcome.error) : unavailableNotice();
	history.value = [];
	step.value = "start";
}

function unavailableNotice(): StartNotice {
	const offer = aiStartOffer.value;
	if (offer.state === "spent")
		return {
			theme: "amber",
			title: __("Today's AI allowance is used up"),
			text: __(
				"Bob can build your site from your description once it renews at midnight UTC, {0}. Until then, start another way.",
				[offer.resetsIn],
			),
		};
	return {
		theme: "amber",
		title: __("Bob isn't available on this site right now"),
		text: __("So it can't build your site from your description. Start another way."),
	};
}

function failedNotice(error: unknown): StartNotice {
	return {
		theme: "red",
		title: __("Bob couldn't start"),
		text: serverMessage(
			error,
			__("Something went wrong on our side. Try again in a moment, or start another way."),
		),
	};
}

function choose(path: "describe" | "clone" | "template" | "blank") {
	if (path === "describe") return goTo("describe");
	if (promptStart.pending) leaveDescription();
	if (path === "clone") return goTo("clone-address");
	if (path === "template") return goTo("templates");
	telemetry.capture("builder_blank_page_selected", { source: "onboarding" });
	router.push({ name: "builder", params: { pageId: "new" } });
}

async function startCloning() {
	cloneStarting.value = true;
	cloneError.value = "";
	try {
		await start(cloneAddress.value.trim(), cloneLook.value);
		telemetry.capture("builder_clone_started", { look: cloneLook.value });
		history.value = [];
		step.value = "clone-progress";
	} catch (e) {
		cloneError.value = serverMessage(e, __("Couldn't start cloning. Try again in a moment."));
	} finally {
		cloneStarting.value = false;
	}
}

async function startDescribing() {
	describeStarting.value = true;
	describeError.value = "";
	try {
		if (promptStart.pending)
			return settleDescribing(await promptStart.startWith(siteDescription.value, describe));
		await describe(siteDescription.value);
	} catch (e) {
		describeError.value = serverMessage(e, __("Couldn't open a new page. Try again in a moment."));
	} finally {
		describeStarting.value = false;
	}
}

function settleDescribing(outcome: PromptStartOutcome) {
	if (outcome.kind === "failed")
		describeError.value = serverMessage(
			outcome.error,
			__("Couldn't open a new page. Try again in a moment."),
		);
	else settle(outcome);
}

// The user starts another way, so the site forgets the description. With the AI only spent for today, Bob's
// composer keeps it for later.
function leaveDescription() {
	promptStart.discard();
	if (aiStartOffer.value.state !== "spent") return;
	const builderStore = useBuilderStore();
	builderStore.aiPromptDraft = siteDescription.value;
	builderStore.leftPanelActiveTab = "Chat";
}

function retryClone() {
	history.value = ["start"];
	step.value = "clone-address";
}

let submitted = false;
function finishQuestions(skipped = false) {
	if (submitted) return;
	submitted = true;
	const category = answers.use_case && useCaseToCategory[answers.use_case];
	if (category) templateCategoryFilter.value = category;
	markPersonaSurveyDone();

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
	submitPersonaSurvey(props);
}
</script>
