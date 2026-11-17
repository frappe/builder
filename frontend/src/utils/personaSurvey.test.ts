import { call } from "frappe-ui";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { RouteLocationNormalized } from "vue-router";

vi.mock("frappe-ui", () => ({ call: vi.fn() }));
vi.mock("@framework/ui/telemetry", () => ({ useTelemetry: vi.fn() }));
vi.mock("@/data/builderSettings", async () => {
	const { reactive } = await import("vue");
	return {
		builderSettings: reactive({ doc: null, get: { fetched: false, loading: false }, reload: vi.fn() }),
	};
});

import { builderSettings } from "@/data/builderSettings";
import { markPersonaSurveyDone, personaSurveyRedirect } from "./personaSurvey";

const USER = "user@example.com";
const SURVEY = { name: "persona-survey", query: {} };
const home = (query = {}) => ({ name: "home", path: "/", query }) as unknown as RouteLocationNormalized;

// what the guard settles on before any timer fires, so without waiting on a request
const atOnce = (redirect: Promise<unknown>) =>
	Promise.race([redirect, new Promise((resolve) => setTimeout(() => resolve("still waiting"), 0))]);

// what the app's own settings load ends in
function settingsLoaded(doc: { persona_survey_done: 0 | 1 }) {
	builderSettings.doc = doc;
	builderSettings.get.fetched = true;
	builderSettings.get.loading = false;
}

beforeEach(() => {
	builderSettings.doc = null;
	builderSettings.get.fetched = false;
	builderSettings.get.loading = false;
	vi.mocked(builderSettings.reload).mockReset();
	vi.mocked(call).mockReset().mockResolvedValue(undefined);
});

afterEach(() => {
	vi.unstubAllGlobals();
	vi.useRealTimers();
});

describe("persona survey redirect", () => {
	beforeEach(() => {
		vi.stubGlobal("window", { is_fc_site: "True", persona_survey_done: false });
		// the app's settings load is still out
		builderSettings.get.loading = true;
	});

	it("sends a user who owes the survey there without waiting for Builder Settings", async () => {
		expect(await atOnce(personaSurveyRedirect(home(), USER))).toEqual(SURVEY);
		expect(builderSettings.reload).not.toHaveBeenCalled();
	});

	it("opens the dashboard for a user who took the survey without waiting for Builder Settings", async () => {
		window.persona_survey_done = true;

		expect(await atOnce(personaSurveyRedirect(home(), USER))).toBeUndefined();
		expect(builderSettings.reload).not.toHaveBeenCalled();
	});

	// the boot data says "not done" for the rest of the page's life
	it("lets the user through once the survey is left, and saves that", async () => {
		markPersonaSurveyDone();

		expect(await personaSurveyRedirect(home(), USER)).toBeUndefined();
		expect(call).toHaveBeenCalledWith("frappe.client.set_value", {
			doctype: "Builder Settings",
			name: "Builder Settings",
			fieldname: { persona_survey_done: 1 },
		});
	});

	// the copy cached in this browser can be out of date
	it("goes by the boot data, not the settings copy cached in this browser", async () => {
		builderSettings.doc = { persona_survey_done: 1 };

		expect(await personaSurveyRedirect(home(), USER)).toEqual(SURVEY);
	});

	it.each([{ is_fc_site: "True" }, { cloud_settings: { enabled: true } }])(
		"runs on Frappe Cloud (%o)",
		async (site) => {
			vi.stubGlobal("window", { ...site, persona_survey_done: false });

			expect(await personaSurveyRedirect(home(), USER)).toEqual(SURVEY);
		},
	);

	it("leaves other sites and guests alone", async () => {
		expect(await personaSurveyRedirect(home(), "Guest")).toBeUndefined();
		vi.stubGlobal("window", { persona_survey_done: false });
		expect(await personaSurveyRedirect(home(), USER)).toBeUndefined();
	});

	it("shows the survey anywhere, even once taken, with ?persona_survey=test", async () => {
		vi.stubGlobal("window", { persona_survey_done: true });

		expect(await personaSurveyRedirect(home({ persona_survey: "test" }), USER)).toEqual({
			name: "persona-survey",
			query: { persona_survey: "test" },
		});
	});
});

// the vite dev server renders no boot data, so the guard asks Builder Settings
describe("persona survey redirect without boot data", () => {
	beforeEach(() => vi.stubGlobal("window", { is_fc_site: "True" }));

	it("sends a user who owes the survey there once the app's settings load lands", async () => {
		builderSettings.get.loading = true;
		const redirect = personaSurveyRedirect(home(), USER);
		settingsLoaded({ persona_survey_done: 0 });

		expect(await redirect).toEqual(SURVEY);
		expect(builderSettings.reload).not.toHaveBeenCalled();
	});

	// the browser's cached copy still says "not done" right after the survey
	it("goes by the server's settings, not the copy cached in this browser", async () => {
		builderSettings.doc = { persona_survey_done: 0 };
		builderSettings.get.loading = true;
		const redirect = personaSurveyRedirect(home(), USER);
		settingsLoaded({ persona_survey_done: 1 });

		expect(await redirect).toBeUndefined();
	});

	it("loads the settings again when the app's load failed, and opens the dashboard if that fails too", async () => {
		builderSettings.doc = { persona_survey_done: 0 };
		vi.mocked(builderSettings.reload).mockImplementation(() => {
			builderSettings.get.loading = true;
			return Promise.resolve().then(() => {
				builderSettings.get.loading = false;
				throw new Error("Internal Server Error");
			});
		});

		expect(await personaSurveyRedirect(home(), USER)).toBeUndefined();
		expect(builderSettings.reload).toHaveBeenCalledOnce();
	});

	it("opens the dashboard when the settings load stalls", async () => {
		vi.useFakeTimers();
		builderSettings.doc = { persona_survey_done: 0 };
		builderSettings.get.loading = true;
		const redirect = personaSurveyRedirect(home(), USER);
		await vi.advanceTimersByTimeAsync(3_000);

		expect(await redirect).toBeUndefined();
	});
});
