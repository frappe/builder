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
import { reactive } from "vue";

const resource = { data: null as unknown[] | null, fetch: vi.fn() };
const call = vi.fn();
let lastResourceConfig:
	{ params?: Record<string, unknown>; transform?: (data: unknown) => unknown } | undefined;
const documentResources = new Map<string, { doc: unknown; reload: ReturnType<typeof vi.fn> }>();
const grantsResources = new Map<string, { data: unknown; reload: ReturnType<typeof vi.fn> }>();

vi.mock("frappe-ui", () => ({
	call,
	createResource: (config: typeof lastResourceConfig) => {
		lastResourceConfig = config;
		return resource;
	},
	createDocumentResource: (config: { name: string }) => {
		const documentResource = reactive({ doc: null as unknown, reload: vi.fn().mockResolvedValue(null) });
		documentResources.set(config.name, documentResource);
		return documentResource;
	},
	getCachedDocumentResource: (_doctype: string, name: string) => documentResources.get(name) ?? null,
	createListResource: (config: { filters?: [string, string, string][] }) => {
		const installationId = config.filters?.[0]?.[2] as string;
		const grantsResource = reactive({ data: [] as unknown[], reload: vi.fn().mockResolvedValue(null) });
		grantsResources.set(installationId, grantsResource);
		return grantsResource;
	},
	onDocUpdate: vi.fn(),
	frappeRequest: vi.fn(),
	setConfig: vi.fn(),
}));

const summary = (name: string) => ({
	installation_id: `${name}-id`,
	name,
	label: name,
	description: `${name} description`,
	icon: `${name}.svg`,
});
const document = (name: string, capabilities: string[] = []) => ({
	extension: name,
	label: name,
	description: `${name} description`,
	enabled: 1,
	checksum: `${name}-checksum`,
	granted_capabilities: JSON.stringify(capabilities),
});
const development = (name: string) => ({
	name,
	label: name,
	entry: `/${name}.js`,
	capabilities: [],
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

/** Seed the cache `getCachedDocumentResource` reads, as if `loadExtensions` had fetched it. */
const seedInstallationDocument = (installationId: string, doc: ReturnType<typeof document>) => {
	documentResources.set(installationId, reactive({ doc, reload: vi.fn().mockResolvedValue(null) }));
};

/** One row `findInstallation` reads from `get_user_installations`, disabled or not. */
const installationRow = (name: string, overrides: Partial<Record<string, unknown>> = {}) => ({
	name,
	installation_id: `${name}-id`,
	label: name,
	description: `${name} description`,
	icon: `${name}.svg`,
	version: "1.0.0",
	source_url: "",
	enabled: true,
	...overrides,
});

/** The fields `useInstallationDetails` reads off the document that the mount list never needs. */
const detailsDocument = (name: string, overrides: Partial<Record<string, unknown>> = {}) => ({
	extension: name,
	readme: undefined,
	installed_on: "2026-09-03 10:00:00",
	requested_capabilities: JSON.stringify(["block.update", "data.access", "schema.write"]),
	granted_capabilities: JSON.stringify(["block.update", "data.access", "schema.write"]),
	...overrides,
});

const seedInstallationGrants = (installationId: string, grants: unknown[]) => {
	const resource = grantsResources.get(installationId);
	if (resource) resource.data = grants;
};

let modules: Awaited<ReturnType<typeof loadModule>>;

describe("installedExtensions", () => {
	beforeEach(async () => {
		resource.data = null;
		call.mockReset();
		documentResources.clear();
		modules = await loadModule();
	});

	it("is empty before the records arrive", () => {
		expect(modules.list.value).toEqual([]);
	});

	it("is the enabled records", () => {
		resource.data = [summary("acme/icons")];
		seedInstallationDocument("acme/icons-id", document("acme/icons"));

		expect(modules.list.value.map((extension) => extension.name)).toEqual(["acme/icons"]);
	});

	it("appends the dev extension", () => {
		resource.data = [summary("acme/icons")];
		seedInstallationDocument("acme/icons-id", document("acme/icons"));
		modules.dev.devExtension.value = development("acme/other");

		expect(modules.list.value.map((extension) => extension.name)).toEqual(["acme/icons", "acme/other"]);
	});

	it("replaces the installed record of the same name", () => {
		resource.data = [summary("acme/icons"), summary("acme/other")];
		seedInstallationDocument("acme/icons-id", document("acme/icons"));
		seedInstallationDocument("acme/other-id", document("acme/other"));
		modules.dev.devExtension.value = {
			...development("acme/icons"),
			entry: "http://localhost:5173/src/main.js",
		};

		expect(modules.list.value).toEqual([
			{
				name: "acme/other",
				label: "acme/other",
				description: "acme/other description",
				icon: "acme/other.svg",
				checksum: "acme/other-checksum",
				capabilities: [],
			},
			{ ...development("acme/icons"), entry: "http://localhost:5173/src/main.js" },
		]);
	});

	it("drops the dev extension when it stops, leaving the record behind", () => {
		resource.data = [summary("acme/icons")];
		seedInstallationDocument("acme/icons-id", document("acme/icons"));
		modules.dev.devExtension.value = development("acme/icons");
		modules.dev.stopDevExtension();

		expect(modules.list.value).toEqual([
			{
				name: "acme/icons",
				label: "acme/icons",
				description: "acme/icons description",
				icon: "acme/icons.svg",
				checksum: "acme/icons-checksum",
				capabilities: [],
			},
		]);
	});
});

describe("useInstallationDetails", () => {
	beforeEach(async () => {
		resource.data = null;
		call.mockReset();
		documentResources.clear();
		grantsResources.clear();
		modules = await loadModule();
	});

	const grants = [{ document_type: "ToDo", can_read: 1, can_write: 0, can_delete: 0, denied: 0 }];

	const running = () =>
		Object.assign(development("acme/icons"), {
			label: "Icons",
			description: "Add and manage icons.",
			version: "1.2.0",
			serverOrigin: "http://localhost:5173",
			readme: "# Icons\n\nDevelopment documentation.",
			capabilities: ["block.update"],
		});

	/** Reload creates the document and grants resources; fill them in once they exist. */
	const openDetails = async (name: string, documentOverrides: Partial<Record<string, unknown>> = {}) => {
		resource.data = [installationRow(name)];
		const installation = modules.data.useInstallationDetails(name);
		await installation.reload();

		documentResources.get(`${name}-id`)!.doc = detailsDocument(name, documentOverrides);
		seedInstallationGrants(`${name}-id`, grants);
		return installation.details.value!;
	};

	it("requests the document and the grants for this installation", async () => {
		resource.data = [installationRow("acme/icons")];

		await modules.data.useInstallationDetails("acme/icons").reload();

		expect(documentResources.has("acme/icons-id")).toBe(true);
		expect(grantsResources.has("acme/icons-id")).toBe(true);
	});

	it("lets the dev server answer for what it shows a user", async () => {
		modules.dev.devExtension.value = running();

		const details = await openDetails("acme/icons");

		expect(details).toMatchObject({
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
	it("lets the record answer for the capabilities, which a user can narrow", async () => {
		modules.dev.devExtension.value = running();

		const details = await openDetails("acme/icons", {
			granted_capabilities: JSON.stringify(["block.update"]),
		});

		expect(details.requested_capabilities).toEqual(["block.update", "data.access", "schema.write"]);
		expect(details.granted_capabilities).toEqual(["block.update"]);
	});

	it("keeps the grants and the install date, which only the record holds", async () => {
		modules.dev.devExtension.value = running();

		const details = await openDetails("acme/icons");

		expect(details.grants).toEqual(grants);
		expect(details.installed_on).toBe("2026-09-03 10:00:00");
	});

	it("answers with the record untouched for an installed extension", async () => {
		const details = await openDetails("acme/icons");

		expect(details).toMatchObject({
			name: "acme/icons",
			label: "acme/icons",
			requested_capabilities: ["block.update", "data.access", "schema.write"],
			granted_capabilities: ["block.update", "data.access", "schema.write"],
			grants,
			installed_on: "2026-09-03 10:00:00",
		});
	});
});
