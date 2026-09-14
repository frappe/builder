/**
 * @vitest-environment jsdom
 *
 * The editor and the panel read one list of records. The editor runs the enabled
 * ones plus the one dev extension, and the two can name the same extension.
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
const doctypeGrantsResources = new Map<string, { data: unknown; reload: ReturnType<typeof vi.fn> }>();
let catalog: { data: { extensions: unknown[] } } | null = null;

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
	getCachedResource: () => catalog,
	createListResource: (config: { filters?: [string, string, string][] }) => {
		const installationId = config.filters?.[0]?.[2] as string;
		const doctypeGrantsResource = reactive({
			data: [] as unknown[],
			reload: vi.fn().mockResolvedValue(null),
		});
		doctypeGrantsResources.set(installationId, doctypeGrantsResource);
		return doctypeGrantsResource;
	},
	onDocUpdate: vi.fn(),
	frappeRequest: vi.fn(),
	setConfig: vi.fn(),
}));

/** One row of `get_user_installations`, which the editor and the panel both read. */
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
const developmentRow = (name: string) =>
	installationRow(name, { version: "0.0.0-dev", is_development: true });
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

/** The fields `useInstallationDetails` reads off the document that the mount list never needs. */
const detailsDocument = (name: string, overrides: Partial<Record<string, unknown>> = {}) => ({
	extension: name,
	readme: undefined,
	installed_on: "2026-09-03 10:00:00",
	requested_capabilities: JSON.stringify(["block.update", "data.access", "schema.write"]),
	granted_capabilities: JSON.stringify(["block.update", "data.access", "schema.write"]),
	...overrides,
});

const seedInstallationDoctypeGrants = (installationId: string, doctypeGrants: unknown[]) => {
	const resource = doctypeGrantsResources.get(installationId);
	if (resource) resource.data = doctypeGrants;
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
		resource.data = [installationRow("acme/icons")];
		seedInstallationDocument("acme/icons-id", document("acme/icons"));

		expect(modules.list.value.map((extension) => extension.name)).toEqual(["acme/icons"]);
	});

	it("appends the dev extension", () => {
		resource.data = [installationRow("acme/icons")];
		seedInstallationDocument("acme/icons-id", document("acme/icons"));
		modules.dev.devExtension.value = development("acme/other");

		expect(modules.list.value.map((extension) => extension.name)).toEqual(["acme/icons", "acme/other"]);
	});

	it("replaces the installed record of the same name", () => {
		resource.data = [installationRow("acme/icons"), installationRow("acme/other")];
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

	it("never mounts a development record, which has no files", () => {
		resource.data = [developmentRow("acme/icons")];
		seedInstallationDocument("acme/icons-id", document("acme/icons"));

		expect(modules.list.value).toEqual([]);
	});

	it("fetches the documents of the rows it mounts, and no others", async () => {
		resource.fetch.mockResolvedValueOnce([
			installationRow("acme/icons"),
			installationRow("acme/off", { enabled: false }),
			developmentRow("acme/dev"),
		]);

		await modules.data.loadExtensions();

		expect(documentResources.has("acme/icons-id")).toBe(true);
		expect(documentResources.has("acme/off-id")).toBe(false);
		expect(documentResources.has("acme/dev-id")).toBe(false);
	});

	it("drops the dev extension when it stops, leaving the record behind", () => {
		resource.data = [installationRow("acme/icons")];
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

describe("userInstallations", () => {
	beforeEach(async () => {
		resource.data = null;
		catalog = { data: { extensions: [{ name: "acme/icons", icon: "https://hub.example.com/icons.svg" }] } };
		modules = await loadModule();
	});

	const iconOf = () => modules.data.userInstallations.value[0].icon;

	it("borrows the catalog icon while the package is not written yet", () => {
		resource.data = [installationRow("acme/icons", { icon: undefined, install_state: "Installing" })];
		expect(iconOf()).toBe("https://hub.example.com/icons.svg");
	});

	it("keeps no icon for a ready package that ships none", () => {
		resource.data = [installationRow("acme/icons", { icon: undefined, install_state: "Ready" })];
		expect(iconOf()).toBeUndefined();
	});

	it("leads with the dev extension, which is always enabled", () => {
		resource.data = [installationRow("acme/listed", { enabled: false }), installationRow("acme/icons")];
		modules.dev.devExtension.value = development("acme/icons");

		expect(modules.data.userInstallations.value.map((row) => row.name)).toEqual([
			"acme/icons",
			"acme/listed",
		]);
	});

	it("hides a development record that no dev server runs this session", () => {
		resource.data = [developmentRow("acme/stale"), installationRow("acme/icons")];

		expect(modules.data.userInstallations.value.map((row) => row.name)).toEqual(["acme/icons"]);
	});

	it("shows what the dev server serves on the record the load made", () => {
		resource.data = [developmentRow("acme/icons")];
		modules.dev.devExtension.value = { ...development("acme/icons"), label: "Icons", version: "1.2.0" };

		expect(modules.data.userInstallations.value).toMatchObject([
			{ installation_id: "acme/icons-id", label: "Icons", version: "1.2.0", is_development: true },
		]);
	});

	it("lends the same icon to the details page", async () => {
		resource.data = [installationRow("acme/icons", { icon: undefined, install_state: "Failed" })];
		const installation = modules.data.useInstallationDetails("acme/icons");
		await installation.reload();
		documentResources.get("acme/icons-id")!.doc = detailsDocument("acme/icons");

		expect(installation.details.value!.icon).toBe("https://hub.example.com/icons.svg");
	});
});

describe("useInstallationDetails", () => {
	beforeEach(async () => {
		resource.data = null;
		call.mockReset();
		documentResources.clear();
		doctypeGrantsResources.clear();
		modules = await loadModule();
	});

	const doctypeGrants = [
		{ document_type: "ToDo", read_access: "allowed", write_access: "not asked", delete_access: "not asked" },
	];

	const running = () =>
		Object.assign(development("acme/icons"), {
			label: "Icons",
			description: "Add and manage icons.",
			version: "1.2.0",
			serverOrigin: "http://localhost:5173",
			readme: "# Icons\n\nDevelopment documentation.",
			capabilities: ["block.update"],
		});

	/** Reload creates the document and doctype-grants resources; fill them in once they exist. */
	const openDetails = async (
		name: string,
		documentOverrides: Partial<Record<string, unknown>> = {},
		row = installationRow(name),
	) => {
		resource.data = [row];
		const installation = modules.data.useInstallationDetails(name);
		await installation.reload();

		documentResources.get(`${name}-id`)!.doc = detailsDocument(name, documentOverrides);
		seedInstallationDoctypeGrants(`${name}-id`, doctypeGrants);
		return installation.details.value!;
	};

	it("requests the document and the doctype grants for this installation", async () => {
		resource.data = [installationRow("acme/icons")];

		await modules.data.useInstallationDetails("acme/icons").reload();

		expect(documentResources.has("acme/icons-id")).toBe(true);
		expect(doctypeGrantsResources.has("acme/icons-id")).toBe(true);
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

	it("opens the record a dev server load made, which the server lists", async () => {
		modules.dev.devExtension.value = running();

		const details = await openDetails("acme/icons", {}, developmentRow("acme/icons"));

		expect(details).toMatchObject({
			label: "Icons",
			is_development: true,
			installed_on: "2026-09-03 10:00:00",
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

	it("keeps the doctype grants and the install date, which only the record holds", async () => {
		modules.dev.devExtension.value = running();

		const details = await openDetails("acme/icons");

		expect(details.doctype_grants).toEqual(doctypeGrants);
		expect(details.installed_on).toBe("2026-09-03 10:00:00");
	});

	it("answers with the record untouched for an installed extension", async () => {
		const details = await openDetails("acme/icons");

		expect(details).toMatchObject({
			name: "acme/icons",
			label: "acme/icons",
			requested_capabilities: ["block.update", "data.access", "schema.write"],
			granted_capabilities: ["block.update", "data.access", "schema.write"],
			doctype_grants: doctypeGrants,
			installed_on: "2026-09-03 10:00:00",
		});
	});
});
