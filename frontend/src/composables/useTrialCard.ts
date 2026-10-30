import { __ } from "@/translation";
import { closeCloudSettings, isCloudSettingsAvailable, openCloudSettings } from "@frappe/cloud-sdk";
import { getBilling, type BillingTrial, type CloudContext } from "@frappe/cloud-sdk/api";
import { StorageSerializers, useStorage } from "@vueuse/core";
import { toast } from "frappe-ui";
import { computed, onUnmounted, ref } from "vue";

// days left change once a day, and each fetch goes through Pilot and Central
const CACHE_MS = 6 * 60 * 60 * 1000;
const DISMISS_MS = 24 * 60 * 60 * 1000;
const URGENT_DAYS = 3;

declare global {
	interface Window {
		cloud_settings?: CloudContext;
	}
}

type CachedTrial = { trial: BillingTrial | null; fetchedAt: number };

export type TrialCardContent = {
	theme: "gray" | "amber" | "red";
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
	const date = new Date(deletesOn).toLocaleDateString(undefined, { day: "numeric", month: "short" });
	return __("Your site will be deleted on {0}. Choose a plan to keep it.", [date]);
}

export function getTrialCardContent(trial: BillingTrial): TrialCardContent {
	if (trial.state === "Ended") {
		return {
			theme: "red",
			title: __("Your trial has ended"),
			description: getDeletionNotice(trial.deletes_on),
			actionLabel: __("Choose a plan"),
			dismissible: false,
		};
	}
	if (trial.held) {
		return {
			theme: "amber",
			title: __("Your plan is over your spending limit"),
			description: __("Raise the limit or choose a smaller plan to end your trial."),
			actionLabel: __("Manage billing"),
			dismissible: true,
		};
	}
	return {
		theme: trial.days_left <= URGENT_DAYS ? "amber" : "gray",
		title: getEndsInTitle(trial.days_left),
		description: __("Choose a plan to keep your site after the trial."),
		actionLabel: __("Choose a plan"),
		dismissible: true,
	};
}

/** The site's Frappe Cloud v2 trial for the dashboard sidebar. System Managers only. */
export function useTrialCard() {
	const context = window.cloud_settings;
	const isAvailable = ref(false);
	const cached = useStorage<CachedTrial | null>("builderTrialCard", null, undefined, {
		serializer: StorageSerializers.object,
	});
	const dismissedAt = useStorage("builderTrialCardDismissedAt", 0);
	const opening = ref(false);

	const refresh = () =>
		getBilling()
			.then(({ trial }) => (cached.value = { trial: trial ?? null, fetchedAt: Date.now() }))
			.catch((error) => console.error("Could not read the trial", error));

	// the vite dev server has no boot payload, so the SDK asks the site instead
	isCloudSettingsAvailable(context)
		.then((available) => {
			isAvailable.value = available;
			if (available && Date.now() - (cached.value?.fetchedAt ?? 0) >= CACHE_MS) refresh();
		})
		.catch((error) => console.error("Could not check Cloud Settings", error));
	onUnmounted(closeCloudSettings);

	const content = computed(() => {
		const trial = isAvailable.value ? cached.value?.trial : null;
		if (!trial) return null;
		const isDismissed = Date.now() - dismissedAt.value < DISMISS_MS;
		return isDismissed && trial.state !== "Ended" ? null : getTrialCardContent(trial);
	});

	async function openBilling() {
		opening.value = true;
		try {
			await openCloudSettings({
				context,
				panels: ["billing", "advanced"],
				tab: "billing",
				theme: "auto",
				// choosing a plan ends the trial
				onClose: refresh,
			});
		} catch (error) {
			toast.error(error instanceof Error ? error.message : __("Could not open Cloud Settings"));
		} finally {
			opening.value = false;
		}
	}

	const dismiss = () => (dismissedAt.value = Date.now());

	return { content, opening, openBilling, dismiss };
}
