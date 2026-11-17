import { builderSettings } from "@/data/builderSettings";
import { useTelemetry } from "@framework/ui/telemetry";
import { until } from "@vueuse/core";
import { call } from "frappe-ui";
import type { RouteLocationNormalized, RouteLocationRaw } from "vue-router";

// Frappe Cloud can write the Pulse key after the user's first visit, so answers given
// before that wait here, in this browser, until telemetry is on.
const PENDING_KEY = "builder_persona_survey_pending";
// the Pulse client loads from a remote script, and a content blocker can stop it for good
const CLIENT_WAIT_MS = 30_000;
// Only the vite dev server, which renders no boot data, asks Builder Settings. A load slower than
// this opens the dashboard, and the survey shows the next time the user opens it.
const SETTINGS_WAIT_MS = 3_000;

declare global {
	interface Window {
		telemetry_enabled?: boolean;
		persona_survey_done?: boolean;
	}
}

export type PersonaAnswers = Record<string, string | boolean | null>;

// A guard on the home route, so a user who owes the survey is sent there before the dashboard renders.
// The survey runs on Frappe Cloud sites only; ?persona_survey=test forces it elsewhere.
export async function personaSurveyRedirect(
	to: RouteLocationNormalized,
	user: string,
): Promise<RouteLocationRaw | undefined> {
	const forced = to.query.persona_survey === "test";
	if (!isCloudSite() && !forced) return;
	if (!user || user === "Guest") return;
	if (!forced && (await isPersonaSurveyDone())) return;
	return { name: "persona-survey", query: forced ? { persona_survey: "test" } : {} };
}

// Leaving the questions settles the survey, so the guard lets the user through from now on.
// A failed save must never block the user from moving on.
export function markPersonaSurveyDone() {
	window.persona_survey_done = true;
	// the survey can open before Builder Settings has loaded, and its resource can't save until then
	call("frappe.client.set_value", {
		doctype: "Builder Settings",
		name: "Builder Settings",
		fieldname: { persona_survey_done: 1 },
	}).catch((e: unknown) => console.error("[persona-survey] failed to persist", e));
}

export function submitPersonaSurvey(answers: PersonaAnswers) {
	if (window.telemetry_enabled) return send(answers);
	save(answers);
}

export function sendPendingPersonaSurvey() {
	if (!window.telemetry_enabled) return;
	let pending: PersonaAnswers | null = null;
	try {
		pending = JSON.parse(localStorage.getItem(PENDING_KEY) || "null");
	} catch (e) {
		console.error("[persona-survey] could not read the saved answers", e);
	}
	if (pending) send(pending);
}

async function send(answers: PersonaAnswers) {
	call("builder.api.identify_persona", {
		role: answers.role,
		use_case: answers.use_case,
		source: answers.source,
	}).catch((e: unknown) => console.error("[persona-survey] failed to identify", e));

	const telemetry = useTelemetry();
	const isReady = await until(() => telemetry.isEnabled).toBe(true, { timeout: CLIENT_WAIT_MS });
	// capture does nothing while telemetry is off, so keep the answers for the next app start
	if (!isReady) return save(answers);
	try {
		telemetry.capture("builder_persona_submitted", answers);
		localStorage.removeItem(PENDING_KEY);
	} catch (e) {
		console.error("[persona-survey] failed to capture", e);
	}
}

function save(answers: PersonaAnswers) {
	try {
		localStorage.setItem(PENDING_KEY, JSON.stringify({ submitted_at: new Date().toISOString(), ...answers }));
	} catch (e) {
		console.error("[persona-survey] could not save the answers", e);
	}
}

// is_fc_site reads a key only Frappe Cloud V1 sites have, and V2 sites carry Cloud Settings instead
function isCloudSite() {
	return window.is_fc_site === "True" || Boolean(window.cloud_settings?.enabled);
}

// The page renders the flag as it stood on load, so the guard decides with no request.
async function isPersonaSurveyDone() {
	if (window.persona_survey_done !== undefined) return window.persona_survey_done;
	const settings = await loadedBuilderSettings();
	return !settings || Boolean(settings.persona_survey_done);
}

// The server's copy: the one cached in this browser still says "not done" after the survey, as a save
// does not refresh it. A failed or slow load gives null, so it never holds the dashboard back.
async function loadedBuilderSettings() {
	const { get } = builderSettings;
	if (!get.fetched && !get.loading) builderSettings.reload().catch(() => {});
	await until(() => get.loading).toBe(false, { timeout: SETTINGS_WAIT_MS });
	return get.fetched ? builderSettings.doc : null;
}
