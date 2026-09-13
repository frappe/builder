/**
 * @vitest-environment jsdom
 *
 * What the editor runs is the enabled records plus the one dev extension, and
 * the two lists can name the same extension.
 *
 * `devExtension.ts` listens for `pagehide` at module scope, so importing the
 * list at all needs a window.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const resource = { data: null as unknown[] | null, fetch: vi.fn() };
const call = vi.fn();
let lastResourceConfig: { params?: Record<string, unknown>; transform?: (data: unknown) => unknown } | undefined;

vi.mock("frappe-ui", () => ({
	call,
	createResource: (config: typeof lastResourceConfig) => {
		lastResourceConfig = config;
		return resource;
	},
	createDocumentResource: () => resource,
	frappeRequest: vi.fn(),
	setConfig: vi.fn(),
}));

const installed = (name: string) => ({ name, label: name, entry: `/${name}.js`, capabilities: [] });
const development = (name: string) => ({
	...installed(name),
	version: "1.0.0",
	serverOrigin: "http://localhost:5173",
});

const loadModule = async () => {
	vi.resetModules();
	const data = await import("../extensions");
	return {
		data,
		list: data.installedExtensions,
		dev: await import("@/extensions/devExtension"),
	};
};

let modules: Awaited<ReturnType<typeof loadModule>>;

describe("installedExtensions", () => {
	beforeEach(async () => {
		resource.data = null;
		call.mockReset();
		modules = await loadModule();
	});

	it("is empty before the records arrive", () => {
		expect(modules.list.value).toEqual([]);
	});

	it("is the enabled records", () => {
		resource.data = [installed("acme/icons")];

		expect(modules.list.value.map((extension) => extension.name)).toEqual(["acme/icons"]);
	});

	it("appends the dev extension", () => {
		resource.data = [installed("acme/icons")];
		modules.dev.devExtension.value = development("acme/other");

		expect(modules.list.value.map((extension) => extension.name)).toEqual(["acme/icons", "acme/other"]);
	});

	it("replaces the installed record of the same name", () => {
		resource.data = [installed("acme/icons"), installed("acme/other")];
		modules.dev.devExtension.value = {
			...development("acme/icons"),
			entry: "http://localhost:5173/src/main.js",
		};

		expect(modules.list.value).toEqual([
			installed("acme/other"),
			{ ...development("acme/icons"), entry: "http://localhost:5173/src/main.js" },
		]);
	});

	it("drops the dev extension when it stops, leaving the record behind", () => {
		resource.data = [installed("acme/icons")];
		modules.dev.devExtension.value = development("acme/icons");
		modules.dev.stopDevExtension();

		expect(modules.list.value).toEqual([installed("acme/icons")]);
	});
});

describe("getInstallationDetails", () => {
	beforeEach(async () => {
		resource.data = null;
		call.mockReset();
		lastResourceConfig = undefined;
		modules = await loadModule();
	});

	const recorded = {
		name: "acme/icons",
		label: "the label the record was written with",
		version: "0.0.0-dev",
		readme: undefined,
		requested_capabilities: ["block.update", "data.access", "schema.write"],
		granted_capabilities: ["block.update", "data.access", "schema.write"],
		grants: [{ document_type: "ToDo", can_read: 1, can_write: 0, can_delete: 0, denied: 0 }],
		installed_on: "2026-09-03 10:00:00",
	};

	const running = () =>
		Object.assign(development("acme/icons"), {
			label: "Icons",
			description: "Add and manage icons.",
			version: "1.2.0",
			serverOrigin: "http://localhost:5173",
			readme: "# Icons\n\nDevelopment documentation.",
			capabilities: ["block.update"],
		});

	const transform = (details: unknown) => {
		modules.data.getInstallationDetails("acme/icons");
		return lastResourceConfig!.transform!(details);
	};

	it("requests the record by extension name", () => {
		modules.data.getInstallationDetails("acme/icons");

		expect(lastResourceConfig!.params).toEqual({ extension: "acme/icons" });
	});

	it("lets the dev server answer for what it shows a user", () => {
		modules.dev.devExtension.value = running();

		expect(transform(recorded)).toMatchObject({
			label: "Icons",
			version: "1.2.0",
			development_server: "http://localhost:5173",
			is_development: true,
			readme: "# Icons\n\nDevelopment documentation.",
		});
	});

	/**
	 * The record holds what the user narrowed to, and the entry holds what the
	 * manifest asked for. Reading the entry would show a grant they took back.
	 */
	it("lets the record answer for the capabilities, which a user can narrow", () => {
		modules.dev.devExtension.value = running();

		const details = transform({ ...recorded, granted_capabilities: ["block.update"] }) as typeof recorded;

		expect(details.requested_capabilities).toEqual(recorded.requested_capabilities);
		expect(details.granted_capabilities).toEqual(["block.update"]);
	});

	it("keeps the grants, which only the record holds", () => {
		modules.dev.devExtension.value = running();

		const details = transform(recorded) as typeof recorded;

		expect(details.grants).toEqual(recorded.grants);
		expect(details.installed_on).toBe("2026-09-03 10:00:00");
	});

	it("answers with the record untouched for an installed extension", () => {
		expect(transform(recorded)).toEqual(recorded);
	});
});
