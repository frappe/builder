import { isCloudBillingAvailable, useCloudBilling } from "@/composables/useCloudBilling";
import { isHostEditor, isIsolated, isMounted } from "@/utils/frappePage";
import { call } from "frappe-ui";
import { computed, ref, watch } from "vue";

export type SiteClone = {
	status: string;
	source_url: string;
	events?: { text: string; kind: string }[];
	error?: string;
};

export type CloneLook = "clean_up" | "as_is" | "redesign";

const POLL_MS = 5000;
// the service also logs each file its agent reads; those mean nothing to the site owner
const PROGRESS_KINDS = new Set(["stage", "info", "page", "done", "error"]);
// module-level so onboarding and the dashboard sidebar share one copy of the server's clone state
const clone = ref<SiteClone | null>(null);
let timer: ReturnType<typeof setTimeout> | undefined;
let watching = false;

const done = computed(() => clone.value?.status === "Done");
const failed = computed(() => ["Failed", "Expired"].includes(clone.value?.status ?? ""));
const running = computed(() => Boolean(clone.value) && !done.value && !failed.value);
const host = computed(() => (clone.value ? new URL(clone.value.source_url).host : ""));
const progress = computed(() =>
	(clone.value?.events ?? []).filter((event) => PROGRESS_KINDS.has(event.kind)).map((event) => event.text),
);
const latestStep = computed(() => progress.value.at(-1) ?? "");

async function refresh() {
	clearTimeout(timer);
	clone.value = await call<SiteClone>("builder.clone_onboarding.clone_status").catch(() => clone.value);
	if (running.value) timer = setTimeout(refresh, POLL_MS);
}

async function start(url: string, look: CloneLook) {
	clone.value = await call<SiteClone>("builder.clone_onboarding.start_clone", { url, look });
	timer = setTimeout(refresh, POLL_MS);
}

/** The server's own reason, which frappe-ui's call() attaches to the error it rejects with. */
export function serverMessage(error: unknown, fallback: string): string {
	if (error instanceof Error && "messages" in error && Array.isArray(error.messages) && typeof error.messages[0] === "string")
		return error.messages[0];
	return fallback;
}

// frappe.page sites clone through the same service; they have no Cloud billing to ask.
// The app host's own editor holds only its landing page, so it clones nothing
const available = computed(() => !isHostEditor && (isMounted || isCloudBillingAvailable.value));

/** Frappe Cloud v2 and frappe.page sites only: elsewhere `available` stays false and nothing is fetched. */
export function useSiteClone() {
	if (!isIsolated) useCloudBilling();
	if (!watching) {
		watching = true;
		watch(available, (canClone) => canClone && refresh(), { immediate: true });
	}
	return {
		available,
		clone,
		done,
		failed,
		running,
		host,
		progress,
		latestStep,
		start,
		refresh,
	};
}
