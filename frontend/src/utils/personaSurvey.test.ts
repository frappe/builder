import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { RouteLocationNormalized } from "vue-router";

const frappePage = vi.hoisted(() => ({ isMounted: false }));
vi.mock("@/utils/frappePage", () => frappePage);
vi.mock("frappe-ui", () => ({ call: vi.fn() }));
vi.mock("@framework/ui/telemetry", () => ({ useTelemetry: vi.fn() }));
vi.mock("@/data/builderSettings", async () => {
	const { reactive } = await import("vue");
	return {
		builderSettings: reactive({ doc: null, get: { fetched: false, loading: false }, reload: vi.fn() }),
	};
});

import { builderSettings } from "@/data/builderSettings";
import { personaSurveyRedirect } from "./personaSurvey";

const USER = "user@example.com";
const SURVEY = { name: "persona-survey", query: {} };
const home = (query = {}) => ({ name: "home", path: "/", query }) as unknown as RouteLocationNormalized;

// what the app's own settings load ends in
function settingsLoaded(doc: { persona_survey_done: 0 | 1 }) {
	builderSettings.doc = doc;
	builderSettings.get.fetched = true;
	builderSettings.get.loading = false;
}

describe("persona survey redirect", () => {
	beforeEach(() => {
		vi.stubGlobal("window", { is_fc_site: "True" });
		builderSettings.doc = null;
		builderSettings.get.fetched = false;
		builderSettings.get.loading = false;
		vi.mocked(builderSettings.reload).mockReset();
		frappePage.isMounted = false;
	});

	afterEach(() => {
		vi.unstubAllGlobals();
		vi.useRealTimers();
	});

	it("sends a user who owes the survey there once the app's settings load lands", async () => {
		builderSettings.get.loading = true;
		const redirect = personaSurveyRedirect(home(), USER);
		settingsLoaded({ persona_survey_done: 0 });

		expect(await redirect).toEqual(SURVEY);
		expect(builderSettings.reload).not.toHaveBeenCalled();
	});

	it("opens the dashboard for a user who took the survey", async () => {
		settingsLoaded({ persona_survey_done: 1 });

		expect(await personaSurveyRedirect(home(), USER)).toBeUndefined();
	});

	// the browser's cached copy still says "not done" right after the survey
	it("goes by the server's settings, not the copy cached in this browser", async () => {
		builderSettings.doc = { persona_survey_done: 0 };
		builderSettings.get.loading = true;
		const redirect = personaSurveyRedirect(home(), USER);
		settingsLoaded({ persona_survey_done: 1 });

		expect(await redirect).toBeUndefined();
	});

	it.each([{ is_fc_site: "True" }, { cloud_settings: { enabled: true } }])(
		"runs on Frappe Cloud (%o)",
		async (site) => {
			vi.stubGlobal("window", site);
			settingsLoaded({ persona_survey_done: 0 });

			expect(await personaSurveyRedirect(home(), USER)).toEqual(SURVEY);
		},
	);

	// frappe.page mounts the editor at frappe.page/<sub>, and every new site there owes the survey
	it("runs on frappe.page sites", async () => {
		vi.stubGlobal("window", {});
		frappePage.isMounted = true;
		settingsLoaded({ persona_survey_done: 0 });

		expect(await personaSurveyRedirect(home(), USER)).toEqual(SURVEY);
	});

	it("leaves other sites and guests alone", async () => {
		settingsLoaded({ persona_survey_done: 0 });

		expect(await personaSurveyRedirect(home(), "Guest")).toBeUndefined();
		vi.stubGlobal("window", {});
		expect(await personaSurveyRedirect(home(), USER)).toBeUndefined();
	});

	it("shows the survey anywhere, even once taken, with ?persona_survey=test", async () => {
		vi.stubGlobal("window", {});
		settingsLoaded({ persona_survey_done: 1 });

		expect(await personaSurveyRedirect(home({ persona_survey: "test" }), USER)).toEqual({
			name: "persona-survey",
			query: { persona_survey: "test" },
		});
	});

	it("loads the settings again when the app's load failed, and opens the dashboard if that fails too", async () => {
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
		builderSettings.get.loading = true;
		const redirect = personaSurveyRedirect(home(), USER);
		await vi.advanceTimersByTimeAsync(3_000);

		expect(await redirect).toBeUndefined();
	});
});
