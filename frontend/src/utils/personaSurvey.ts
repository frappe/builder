import { useTelemetry } from "@framework/ui/telemetry";
import { until } from "@vueuse/core";
import { call } from "frappe-ui";

// Frappe Cloud can write the Pulse key after the user's first visit, so answers given
// before that wait here, in this browser, until telemetry is on.
const PENDING_KEY = "builder_persona_survey_pending";
// the Pulse client loads from a remote script, and a content blocker can stop it for good
const CLIENT_WAIT_MS = 30_000;

declare global {
	interface Window {
		telemetry_enabled?: boolean;
	}
}

export type PersonaAnswers = Record<string, string | boolean | null>;

export function submitPersonaSurvey(answers: PersonaAnswers) {
	if (window.telemetry_enabled) return send(answers);
	try {
		localStorage.setItem(PENDING_KEY, JSON.stringify({ ...answers, submitted_at: new Date().toISOString() }));
	} catch (e) {
		console.error("[persona-survey] could not save the answers", e);
	}
}

export function sendPendingPersonaSurvey() {
	if (!window.telemetry_enabled) return;
	let pending: PersonaAnswers | null = null;
	try {
		pending = JSON.parse(localStorage.getItem(PENDING_KEY) || "null");
		localStorage.removeItem(PENDING_KEY);
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
	await until(() => telemetry.isEnabled).toBe(true, { timeout: CLIENT_WAIT_MS });
	try {
		telemetry.capture("builder_persona_submitted", answers);
	} catch (e) {
		console.error("[persona-survey] failed to capture", e);
	}
}
