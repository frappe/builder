import { __ } from "@/translation";
import { isCloudSettingsAvailable, openCloudSettings } from "@frappe/cloud-sdk";
import { getBilling, type BillingSummary, type BillingTrial, type CloudContext } from "@frappe/cloud-sdk/api";
import { StorageSerializers, useStorage } from "@vueuse/core";
import { toast } from "frappe-ui";
import { computed, ref } from "vue";

// days left change once a day, and each fetch goes through Pilot and Central
const CACHE_MS = 6 * 60 * 60 * 1000;
const DISMISS_MS = 24 * 60 * 60 * 1000;
const URGENT_DAYS = 3;

declare global {
	interface Window {
		cloud_settings?: CloudContext;
	}
}

type CachedBilling = { billing: BillingSummary; fetchedAt: number };

export type TrialNotice = {
	theme: "gray" | "amber" | "red";
	badge: string;
	title: string;
	description: string;
	actionLabel: string;
	dismissible: boolean;
};

function getEndsInTitle(daysLeft: number) {
	if (daysLeft <= 0) return __("Your trial ends today");
	if (daysLeft === 1) return __("Your trial ends tomorrow");
	return __("Your trial ends in {0} days", [daysLeft]);
}

function getDeletionNotice(deletesOn: string | null) {
	if (!deletesOn) return __("Choose a plan to keep using your site.");
	// a date-only string parses as UTC midnight, so format in UTC to keep the same day
	const date = new Date(deletesOn).toLocaleDateString(undefined, {
		day: "numeric",
		month: "short",
		timeZone: "UTC",
	});
	return __("Your site will be deleted on {0}. Choose a plan to keep it.", [date]);
}

export function getTrialNotice(trial: BillingTrial): TrialNotice {
	if (trial.state === "Ended") {
		return {
			theme: "red",
			badge: __("Trial ended"),
			title: __("Your trial has ended"),
			description: getDeletionNotice(trial.deletes_on),
			actionLabel: __("Choose a plan"),
			dismissible: false,
		};
	}
	if (trial.held) {
		return {
			theme: "amber",
			badge: __("Over spending limit"),
			title: __("Your plan is over your spending limit"),
			description: __("Raise the limit or choose a smaller plan to end your trial."),
			actionLabel: __("Manage billing"),
			dismissible: true,
		};
	}
	return {
		theme: trial.days_left <= URGENT_DAYS ? "amber" : "gray",
		badge: __("Trial: {0} days left", [Math.max(trial.days_left, 0)]),
		title: getEndsInTitle(trial.days_left),
		description: __("Choose a plan to keep your site after the trial."),
		actionLabel: __("Choose a plan"),
		dismissible: true,
	};
}

// one copy for the dashboard card, the toolbar badge and the billing pane
const isAvailable = ref(false);
const cached = useStorage<CachedBilling | null>("builderCloudBilling", null, undefined, {
	serializer: StorageSerializers.object,
});
const dismissedAt = useStorage("builderTrialCardDismissedAt", 0);
let availabilityCheck: Promise<unknown> | undefined;

const billing = computed(() => (isAvailable.value ? cached.value?.billing : undefined));
const trialNotice = computed(() => (billing.value?.trial ? getTrialNotice(billing.value.trial) : null));
const isTrialCardDismissed = computed(
	() => Boolean(trialNotice.value?.dismissible) && Date.now() - dismissedAt.value < DISMISS_MS,
);

export const isCloudBillingAvailable = computed(() => isAvailable.value);

export const refreshBilling = () =>
	getBilling().then((summary) => (cached.value = { billing: summary, fetchedAt: Date.now() }));

function checkAvailability() {
	// the vite dev server has no boot payload, so the SDK asks the site instead
	availabilityCheck ??= isCloudSettingsAvailable(window.cloud_settings)
		.then((available) => {
			isAvailable.value = available;
			if (available && Date.now() - (cached.value?.fetchedAt ?? 0) >= CACHE_MS) return refreshBilling();
		})
		.catch((error) => console.error("Could not read Cloud Settings billing", error));
}

export const isPlanPickerOpening = ref(false);

export async function openPlanPicker() {
	isPlanPickerOpening.value = true;
	try {
		await openCloudSettings({
			context: window.cloud_settings,
			panels: ["billing"],
			tab: "billing",
			theme: "auto",
			// choosing a plan ends the trial
			onClose: () => refreshBilling().catch((error) => console.error("Could not read the billing", error)),
		});
	} catch (error) {
		toast.error(error instanceof Error ? error.message : __("Could not open Cloud Settings"));
	} finally {
		isPlanPickerOpening.value = false;
	}
}

/** The site's Frappe Cloud v2 billing. System Managers only. */
export function useCloudBilling() {
	checkAvailability();
	const dismissTrialCard = () => (dismissedAt.value = Date.now());
	return { billing, trialNotice, isTrialCardDismissed, dismissTrialCard };
}
