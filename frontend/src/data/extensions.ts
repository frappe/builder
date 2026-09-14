import { devExtension, isDevExtension, setDevCapabilities } from "@/extensions/devExtension";
import type { Access, AccessAnswer } from "@/extensions/data/grants";
import type { Capability, InstalledExtension } from "frappe-builder-extension-sdk/types";
import {
	call,
	createDocumentResource,
	createListResource,
	createResource,
	getCachedResource,
	getCachedDocumentResource,
	onDocUpdate,
} from "frappe-ui";
import { computed, shallowRef } from "vue";
import { builderSettings } from "@/data/builderSettings";

const METHOD = "builder.extensions.installations";
const INSTALLATION_DOCTYPE = "Builder User Extension";
const GRANT_DOCTYPE = "Builder Extension Grant";

const HUB_API = "api/method/builder_hub.extensions.api";
const CATALOG_CACHE = "extensions-catalog";

/** The Builder Hub this site reads its catalog from. */
const hubUrl = () => ensureProtocol(builderSettings.doc?.hub_url ?? "") || "preview.frappe.cloud";

function ensureProtocol(url: string, defaultProtocol = "http") {
	if (!url) return url;

	// Normalize the default protocol (strip any trailing "://" or ":")
	const protocol = defaultProtocol.replace(/:\/\/$|:$/, "");
	// Matches things like "http://", "https://", "ftp://", "mailto:", "//" (protocol-relative)
	const hasProtocol = /^[a-zA-Z][a-zA-Z\d+\-.]*:\/\//.test(url) || /^\/\//.test(url);

	let result = hasProtocol ? url : `${protocol}://${url}`;
	result = result.replace(/\/+$/, "");

	return result;
}

type InstallationDocument = {
	extension: string;
	label?: string;
	description?: string;
	enabled: boolean | number;
	checksum?: string;
	granted_capabilities?: string;
	/** The rest is unread by the mount list, and read only by the details panel. */
	version?: string;
	source_url?: string;
	install_state?: "Installing" | "Ready" | "Failed";
	install_error?: string;
	installed_on?: string;
	readme?: string;
	requested_capabilities?: string;
};

/** The Vue instance a document resource ties its realtime subscription to. Set once, from the editor. */
let resourceVm: unknown;

const grantedCapabilities = (value: string | undefined): Capability[] => {
	if (!value) return [];
	return JSON.parse(value) as Capability[];
};

/**
 * One installation's document, shared by the mount list and the details panel.
 *
 * `frappe-ui` caches this itself by doctype and name, so calling it again for an
 * installation already loaded returns the same live resource rather than a
 * second copy racing it.
 */
const installationDocument = (installationId: string) =>
	createDocumentResource<InstallationDocument>(
		{
			doctype: INSTALLATION_DOCTYPE,
			name: installationId,
			auto: false,
			realtime: Boolean(resourceVm),
			onError: (error: Error) => console.error("Could not load extension", error),
		},
		resourceVm,
	);

/**
 * Every installation of this user, the disabled and development ones included.
 *
 * The editor mounts the enabled rows, and the panel shows them all. One list
 * means one fetch to refresh after a change, so the two never disagree.
 */
const installationsResource = createResource<UserInstallation[]>({
	url: "builder.extensions.installations.get_user_installations",
	// losing this list costs the editor its extensions, never the editor itself
	onError: (error: Error) => console.error("Could not load installations", error),
});

/**
 * Fetch one installation's document into that shared cache.
 *
 * Read it back with `getCachedDocumentResource`, never held here: `toInstalledExtension`
 * only reads that cache, so a fetch never happens as a side effect of a computed.
 */
const loadInstallationDocument = (row: UserInstallation) => {
	void installationDocument(row.installation_id)
		.reload()
		.catch(() => undefined);
};

const toInstalledExtension = (row: UserInstallation): InstalledExtension | null => {
	const document = getCachedDocumentResource<InstallationDocument>(
		INSTALLATION_DOCTYPE,
		row.installation_id,
	)?.doc;
	if (!document || !document.enabled) return null;

	return {
		name: row.name,
		label: document.label ?? row.label ?? row.name,
		description: document.description ?? row.description,
		icon: row.icon,
		checksum: document.checksum,
		capabilities: grantedCapabilities(document.granted_capabilities),
	};
};

/**
 * Every extension this user runs: their installations, plus the one loaded from a
 * dev server this session. A dev extension replaces the installation of the same
 * name, because two entries would give it two frames.
 *
 * A development record never mounts. It has no files, and the browser's own entry
 * runs it.
 */
const installedExtensions = computed<InstalledExtension[]>(() => {
	const installed = (installationsResource.data ?? [])
		.filter((row) => !row.is_development)
		.flatMap((row) => {
			const extension = toInstalledExtension(row);
			return extension ? [extension] : [];
		});
	const development = devExtension.value;
	if (!development) return installed;

	return [...installed.filter((extension) => extension.name !== development.name), development];
});

/** Fetches the list, and the documents of the rows the editor mounts. Call it after every change. */
const loadExtensions = async (vm?: unknown) => {
	if (vm) resourceVm = vm;
	const rows = (await installationsResource.fetch()) ?? [];
	rows.filter((row) => row.enabled && !row.is_development).forEach(loadInstallationDocument);
	return rows;
};

/**
 * The built entry of one installation, which a frame runs from a Blob.
 *
 * The editor reads it, not the frame, because a frame sends no session. Fetched
 * once and shared by the five frames that mount one extension. The checksum joins
 * the key, so a rebuild is fetched again. A failed fetch is dropped, so a
 * reloaded frame asks rather than replaying the error.
 */
const sources = new Map<string, Promise<string>>();

const getExtensionSource = (extension: InstalledExtension): Promise<string> => {
	const key = `${extension.name}@${extension.checksum ?? ""}`;

	const cached = sources.get(key);
	if (cached) return cached;

	const reading = call("builder.extensions.registry.get_extension_source", {
		extension: extension.name,
	}) as Promise<string>;

	const source = reading.catch((error: Error) => {
		sources.delete(key);
		throw error;
	});
	sources.set(key, source);
	return source;
};

/**
 * One installation as the Extensions panel reads it.
 *
 * Not `InstalledExtension`: that is the wire shape an extension's own code sees,
 * and a version number or an install date is none of its business. This carries
 * what the panel shows and the editor never needs.
 */
type UserInstallation = {
	name: string;
	/** The document's own name, not the extension's. */
	installation_id: string;
	label?: string;
	description?: string;
	icon?: string;
	/** For a running dev extension, the version its dev server serves. */
	version: string;
	/** The Builder Hub it came from. Empty for an extension installed from a directory. */
	source_url: string;
	enabled: boolean;
	/** A Hub install is "Installing" until its background job lands, then "Ready" or "Failed". */
	install_state?: "Installing" | "Ready" | "Failed";
	/** Why the last Hub install failed, shown with a Retry. */
	install_error?: string;
	/** Made by a dev server load. Only the one running this session is shown. */
	is_development?: boolean;
};

/** One doctype this user answered for, as `Builder Extension Grant` holds it. */
type ExtensionGrant = {
	document_type: string;
	read_access: AccessAnswer;
	write_access: AccessAnswer;
	delete_access: AccessAnswer;
};

type InstallationDetails = UserInstallation & {
	installed_on: string;
	readme?: string;
	requested_capabilities: Capability[];
	granted_capabilities: Capability[];
	doctype_grants: ExtensionGrant[];
	development_server?: string;
};

/** What only a running dev server knows about its extension. */
const applyDevelopmentDetails = (details: InstallationDetails): InstallationDetails => {
	const development = devExtension.value;
	if (!development || development.name !== details.name) return details;

	return { ...details, readme: development.readme, development_server: development.serverOrigin };
};

/**
 * The install job writes the package icon last, so an Installing or Failed row
 * has none. It borrows the icon the Hub catalog showed before the install.
 */
const withCatalogIcon = (row: UserInstallation): UserInstallation => {
	if (row.icon || !row.install_state || row.install_state === "Ready") return row;
	const catalog: CatalogExtension[] = getCachedResource([CATALOG_CACHE, 1])?.data?.extensions ?? [];
	return { ...row, icon: catalog.find((extension) => extension.name === row.name)?.icon };
};

/** A running dev extension shows what its dev server serves, and is always enabled. */
const withDevelopment = (row: UserInstallation): UserInstallation => {
	const development = devExtension.value;
	if (!development || development.name !== row.name) return row;

	return {
		...row,
		label: development.label,
		description: development.description,
		icon: development.icon,
		version: development.version,
		enabled: true,
		is_development: true,
	};
};

/**
 * What the panel manages, which is not what the editor mounts.
 *
 * `installedExtensions` drops a disabled installation, because a frame must not
 * run for one. The panel keeps it, because turning it back on is the point.
 *
 * A development record that no dev server runs this session is one a closed tab
 * failed to remove, so the panel hides it.
 */
const userInstallations = computed<UserInstallation[]>(() => {
	const devInstallation: UserInstallation[] = [];
	const others: UserInstallation[] = [];
	for (const row of installationsResource.data ?? []) {
		if (isDevExtension(row)) devInstallation.push(withDevelopment(withCatalogIcon(row)));
		else if (!row.is_development) others.push(withCatalogIcon(row));
	}
	return [...devInstallation, ...others];
});

const findInstallation = (extension: string) =>
	userInstallations.value.find((installation) => installation.name === extension);

/**
 * Every installation this has already wired a doctype-grant subscription for.
 *
 * A grant is inserted or deleted rather than only edited, so `createListResource`'s
 * own `realtime` option cannot keep it live: that option only refreshes a row
 * already in the fetched page, never a new one. `onDocUpdate` is the same
 * primitive `createDocumentResource` uses for its own realtime, applied here by
 * hand, once per installation, so a bare reload catches the row it would miss.
 */
const doctypeGrantsSubscribed = new Set<string>();

const installationDoctypeGrants = (installationId: string) => {
	const resource = createListResource<ExtensionGrant>(
		{
			doctype: GRANT_DOCTYPE,
			filters: [["installation", "=", installationId]],
			fields: ["document_type", "read_access", "write_access", "delete_access"],
			orderBy: "document_type asc",
			auto: false,
			cache: ["installation-doctype-grants", installationId],
			onError: (error: Error) => console.error("Could not load extension grants", error),
		},
		resourceVm,
	);

	const socket = (resourceVm as { $socket?: Parameters<typeof onDocUpdate>[0] } | undefined)?.$socket;
	if (socket && !doctypeGrantsSubscribed.has(installationId)) {
		doctypeGrantsSubscribed.add(installationId);
		onDocUpdate(socket, GRANT_DOCTYPE, () => void resource.reload());
	}

	return resource;
};

/**
 * One installation, with the dev server standing in for what it owns.
 *
 * A development installation is real, so the record answers for the capabilities
 * it granted, the doctype grants and the install date. What the dev server shows
 * a user comes from the dev server, which is the copy running right now.
 *
 * Composed from what the mount list and the panel's own list already fetch,
 * rather than a details call of its own: the document carries the readme and the
 * raw capability lists, `findInstallation` carries the icon and the install
 * state, and only the doctype grants are fetched here for the first time.
 */
const useInstallationDetails = (extension: string) => {
	const document = shallowRef<ReturnType<typeof installationDocument> | null>(null);
	const doctypeGrants = shallowRef<ReturnType<typeof installationDoctypeGrants> | null>(null);

	const reload = async () => {
		const installationId = findInstallation(extension)?.installation_id;
		if (!installationId) return;

		document.value = installationDocument(installationId);
		doctypeGrants.value = installationDoctypeGrants(installationId);
		await Promise.all([document.value.reload(), doctypeGrants.value.reload()]);
	};

	const details = computed<InstallationDetails | null>(() => {
		const installation = findInstallation(extension);
		const doc = document.value?.doc;
		if (!installation || !doc) return null;

		return applyDevelopmentDetails({
			...installation,
			installed_on: doc.installed_on ?? "",
			readme: doc.readme,
			requested_capabilities: grantedCapabilities(doc.requested_capabilities),
			granted_capabilities: grantedCapabilities(doc.granted_capabilities),
			doctype_grants: doctypeGrants.value?.data ?? [],
		});
	});

	return { details, reload };
};

/**
 * The three answers that stand for one doctype, answering with the grants after it.
 *
 * "Not asked" lets the extension ask about that access again, and the row stays
 * so the panel keeps listing the doctype. A denied access stops the asking.
 */
const setExtensionGrant = (extension: string, doctype: string, answers: Record<Access, AccessAnswer>) =>
	call(`${METHOD}.set_extension_grant`, { extension, doctype, answers }) as Promise<ExtensionGrant[]>;

/** What the site keeps when a user removes an extension. */
type UninstallSummary = {
	resources: { resource_type: string; count: number }[];
	tokens: number;
	other_users: number;
};

/**
 * Every write below reloads the list, so no caller can leave the panel showing
 * one answer and the editor running another.
 */
const setExtensionEnabled = async (extension: string, enabled: boolean) => {
	await call(`${METHOD}.set_extension_enabled`, { extension, enabled });
	await loadExtensions();
};

const setGrantedCapabilities = async (extension: string, capabilities: Capability[]) => {
	const granted = (await call(`${METHOD}.set_granted_capabilities`, {
		extension,
		capabilities,
	})) as Capability[];
	// the editor runs the browser's own entry for a dev extension, not its record,
	// so the new grant has to reach that entry too
	setDevCapabilities(extension, granted);
	return granted;
};

const uninstallSummary = (extension: string) =>
	call(`${METHOD}.get_uninstall_summary`, { extension }) as Promise<UninstallSummary>;

const uninstallExtension = async (extension: string) => {
	await call(`${METHOD}.uninstall_extension`, { extension });
	await loadExtensions();
};

type CatalogExtension = Pick<UserInstallation, "name" | "label" | "description" | "icon">;

/** One row the Extensions panel opened, and whether this user has it installed. */
type SelectedExtension = {
	name: string;
	isInstalled: boolean;
};

const getExtensionsCatalog = (page: number = 1) =>
	createResource({
		url: `${hubUrl()}/${HUB_API}.get_catalog`,
		params: { page },
		auto: true,
		cache: [CATALOG_CACHE, page],
		initialData: { extensions: [] as CatalogExtension[] },
		onError: (error: Error) => console.error("Could not load extensions list", error),
	});

/** A not-installed extension as its hub page describes it. No grants, no install date. */
type HubExtension = CatalogExtension & {
	version: string;
	readme?: string;
	source_url?: string;
};

/** What `get_extension` sends: the manifest entry beside every release of it. */
type HubExtensionResponse = {
	extension: CatalogExtension & { readme?: string; repository_url?: string };
	releases: { version: string; status: string; published_on: string }[];
};

/** The newest published release, which names the version a fresh install gets. */
const latestVersion = (releases: HubExtensionResponse["releases"]) =>
	releases
		.filter((release) => release.status === "Published")
		.sort((a, b) => b.published_on.localeCompare(a.published_on))[0]?.version ?? "";

/**
 * One extension read from the hub, for the page a user opens before installing.
 *
 * Goes to the hub, not the site, because the site has no record of it yet.
 */
const getHubExtension = async (name: string): Promise<HubExtension> => {
	const { extension, releases }: HubExtensionResponse = await createResource({
		url: `${hubUrl()}/${HUB_API}.get_extension`,
		params: { name },
		onError: (error: Error) => console.error("Could not load extension", error),
	}).fetch();

	return {
		name: extension.name,
		label: extension.label,
		description: extension.description,
		icon: extension.icon,
		readme: extension.readme,
		source_url: extension.repository_url,
		version: latestVersion(releases),
	};
};

/** What one exact release asks for. The listing carries no manifest, so this reads the release. */
const getHubReleaseCapabilities = async (name: string, version: string): Promise<Capability[]> => {
	const { release } = await createResource({
		url: `${hubUrl()}/${HUB_API}.get_extension_release`,
		params: { extension_name: name, version },
	}).fetch();
	return release.manifest?.capabilities ?? [];
};

/**
 * Start a Hub install. The server answers with an "Installing" row and runs the
 * download in a background job, so this resolves fast. The row flips to "Ready"
 * or "Failed" on the `builder_extension_install` realtime event.
 *
 * `version` pins the release whose capabilities the user answered for.
 */
const installFromHub = async (name: string, version: string, capabilities: Capability[]) => {
	await call("builder.extensions.hub.install_from_hub", { name, version, capabilities });
	await loadExtensions();
};

export {
	getExtensionSource,
	getExtensionsCatalog,
	getHubExtension,
	getHubReleaseCapabilities,
	INSTALLATION_DOCTYPE,
	installedExtensions,
	installFromHub,
	loadExtensions,
	setExtensionEnabled,
	setExtensionGrant,
	setGrantedCapabilities,
	uninstallExtension,
	uninstallSummary,
	useInstallationDetails,
	userInstallations,
};

export type {
	CatalogExtension,
	ExtensionGrant,
	HubExtension,
	InstallationDetails,
	SelectedExtension,
	UninstallSummary,
	UserInstallation,
};
