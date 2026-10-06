import { devExtension, isDevExtension, setDevPermissions } from "@/extensions/devExtension";
import type { Permission, InstalledExtension } from "frappe-builder-extension-sdk/types";
import {
	call,
	createDocumentResource,
	createResource,
	getCachedResource,
	getCachedDocumentResource,
} from "frappe-ui";
import { computed, shallowRef } from "vue";
import { builderSettings } from "@/data/builderSettings";

const METHOD = "builder.extensions.installations";
const INSTALLATION_DOCTYPE = "Builder Extension";

const HUB_API = "api/method/builder_hub.extensions.api";
const CATALOG_CACHE = "extensions-catalog";

/** The Builder Hub that gives this site its catalog. */
const hubUrl = () => ensureProtocol(builderSettings.doc?.hub_url ?? "") || "preview.frappe.cloud";

function ensureProtocol(url: string, defaultProtocol = "http") {
	if (!url) return url;

	// remove a trailing "://" or ":" from the default protocol
	const protocol = defaultProtocol.replace(/:\/\/$|:$/, "");
	// matches "http://", "https://", "ftp://", "mailto:" and "//" (a protocol-relative URL)
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
	granted_permissions?: string;
	/** The mount list does not read the fields below. Only the details panel reads them. */
	version?: string;
	source_url?: string;
	install_state?: "Installing" | "Ready" | "Failed";
	install_error?: string;
	installed_on?: string;
	readme?: string;
	requested_permissions?: string;
};

/** The Vue instance for the realtime subscription of a document resource. The editor sets it one time. */
let resourceVm: unknown;

const grantedPermissions = (value: string | undefined): Permission[] => {
	if (!value) return [];
	return JSON.parse(value) as Permission[];
};

/**
 * The document of one installation. The mount list and the details panel share it.
 *
 * `frappe-ui` caches it by doctype and name. A second call for a loaded
 * installation gives the same live resource. It does not make a second copy.
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
 * All installations on this site, with the disabled and development installations.
 *
 * The editor mounts the enabled rows, and the panel shows all rows. With one
 * list, one request updates both after a change. So they always agree.
 */
const installationsResource = createResource<Installation[]>({
	url: "builder.extensions.installations.get_installations",
	// if this list fails, the editor loses its extensions. The editor itself still works
	onError: (error: Error) => console.error("Could not load installations", error),
});

/**
 * True if this user can install, turn on, turn off, change permissions or
 * remove extensions. If not, the panel hides those controls. The server also
 * checks each call.
 */
const managerResource = createResource<boolean>({
	url: "builder.extensions.installations.can_manage_extensions",
	onError: (error: Error) => console.error("Could not check extension access", error),
});

const canManageExtensions = computed(() => Boolean(managerResource.data));

/**
 * Gets the document of one installation into the shared cache.
 *
 * Read it with `getCachedDocumentResource`. Do not keep it here.
 * `toInstalledExtension` only reads the cache. So a computed never starts a fetch.
 */
const loadInstallationDocument = (row: Installation) => {
	void installationDocument(row.installation_id)
		.reload()
		.catch(() => undefined);
};

const toInstalledExtension = (row: Installation): InstalledExtension | null => {
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
		permissions: grantedPermissions(document.granted_permissions),
	};
};

/**
 * All extensions that this editor runs. These are the installations of the
 * site, and the extension from a dev server in this session. A dev extension
 * replaces the installation with the same name. Two entries would give it two frames.
 *
 * A development record never mounts. It has no files. The entry in the browser runs it.
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

/** Gets the list, and the documents of the rows that the editor mounts. Call it after each change. */
const loadExtensions = async (vm?: unknown) => {
	if (vm) resourceVm = vm;
	if (managerResource.data === null) void managerResource.fetch();
	const rows = (await installationsResource.fetch()) ?? [];
	rows.filter((row) => row.enabled && !row.is_development).forEach(loadInstallationDocument);
	return rows;
};

/**
 * The built entry of one installation. A frame runs it from a Blob.
 *
 * The editor gets it, not the frame, because a frame sends no session. The
 * editor gets it one time. The five frames of one extension share it.
 *
 * The key includes the checksum. So the editor gets a new build again. The
 * cache removes a failed request. So a reloaded frame asks again and does not
 * get the old error.
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
 * One installation, as the Extensions panel reads it.
 *
 * This is not `InstalledExtension`. That is the shape that the code of an
 * extension sees, and the extension does not need a version number or an
 * install date. This type has the data that the panel shows and the editor
 * never needs.
 */
type Installation = {
	name: string;
	/** The name of the document, not of the extension. */
	installation_id: string;
	label?: string;
	description?: string;
	icon?: string;
	/** For a running dev extension, the version that its dev server serves. */
	version: string;
	/** The Builder Hub that it came from. Empty for an extension from a directory. */
	source_url: string;
	enabled: boolean;
	/** A Hub install is "Installing" until its background job ends. Then it is "Ready" or "Failed". */
	install_state?: "Installing" | "Ready" | "Failed";
	/** Why the last Hub install failed. The panel shows it with a Retry button. */
	install_error?: string;
	/** A dev server load made this row. The panel shows only the row that runs in this session. */
	is_development?: boolean;
};

type InstallationDetails = Installation & {
	installed_on: string;
	readme?: string;
	requested_permissions: Permission[];
	granted_permissions: Permission[];
	development_server?: string;
};

/** The data about an extension that only its running dev server has. */
const applyDevelopmentDetails = (details: InstallationDetails): InstallationDetails => {
	const development = devExtension.value;
	if (!development || development.name !== details.name) return details;

	return { ...details, readme: development.readme, development_server: development.serverOrigin };
};

/**
 * The install job writes the package icon last. So an Installing or Failed row
 * has no icon. It uses the icon from the Hub catalog.
 */
const withCatalogIcon = (row: Installation): Installation => {
	if (row.icon || !row.install_state || row.install_state === "Ready") return row;
	const catalog: CatalogExtension[] = getCachedResource([CATALOG_CACHE, 1])?.data?.extensions ?? [];
	return { ...row, icon: catalog.find((extension) => extension.name === row.name)?.icon };
};

/** A running dev extension shows the data from its dev server. It is always enabled. */
const withDevelopment = (row: Installation): Installation => {
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
 * The rows that the panel manages. They are not the rows that the editor mounts.
 *
 * `installedExtensions` removes a disabled installation, because no frame must
 * run for it. The panel keeps it, so that the user can turn it on again.
 *
 * If no dev server runs a development record in this session, a closed tab
 * failed to remove it. So the panel hides it.
 */
const installations = computed<Installation[]>(() => {
	const devInstallation: Installation[] = [];
	const others: Installation[] = [];
	for (const row of installationsResource.data ?? []) {
		if (isDevExtension(row)) devInstallation.push(withDevelopment(withCatalogIcon(row)));
		else if (!row.is_development) others.push(withCatalogIcon(row));
	}
	return [...devInstallation, ...others];
});

const findInstallation = (extension: string) =>
	installations.value.find((installation) => installation.name === extension);

/**
 * One installation. For a dev extension, the dev server gives its own data.
 *
 * A development installation is a real record. So the record gives the granted
 * permissions and the install date. The dev server gives the data that a user
 * sees, because the dev server runs the current copy.
 *
 * This uses the data that the mount list and the panel list already have. It
 * makes no request of its own. The document has the readme and the permission
 * lists. `findInstallation` has the icon and the install state.
 */
const useInstallationDetails = (extension: string) => {
	const document = shallowRef<ReturnType<typeof installationDocument> | null>(null);

	const reload = async () => {
		const installationId = findInstallation(extension)?.installation_id;
		if (!installationId) return;

		document.value = installationDocument(installationId);
		await document.value.reload();
	};

	const details = computed<InstallationDetails | null>(() => {
		const installation = findInstallation(extension);
		const doc = document.value?.doc;
		if (!installation || !doc) return null;

		return applyDevelopmentDetails({
			...installation,
			installed_on: doc.installed_on ?? "",
			readme: doc.readme,
			requested_permissions: grantedPermissions(doc.requested_permissions),
			granted_permissions: grantedPermissions(doc.granted_permissions),
		});
	});

	return { details, reload };
};

/** The data that the site keeps when a manager removes an extension. */
type UninstallSummary = {
	resources: { resource_type: string; count: number }[];
	tokens: number;
};

/**
 * Each write below reloads the list. So the panel and the editor always show
 * the same state.
 */
const setExtensionEnabled = async (extension: string, enabled: boolean) => {
	await call(`${METHOD}.set_extension_enabled`, { extension, enabled });
	await loadExtensions();
};

const setGrantedPermissions = async (extension: string, permissions: Permission[]) => {
	const granted = (await call(`${METHOD}.set_granted_permissions`, {
		extension,
		permissions,
	})) as Permission[];
	// for a dev extension, the editor runs the entry in the browser, not the record.
	// So the new permissions must also reach that entry
	setDevPermissions(extension, granted);
	return granted;
};

const uninstallSummary = (extension: string) =>
	call(`${METHOD}.get_uninstall_summary`, { extension }) as Promise<UninstallSummary>;

const uninstallExtension = async (extension: string) => {
	await call(`${METHOD}.uninstall_extension`, { extension });
	await loadExtensions();
};

type CatalogExtension = Pick<Installation, "name" | "label" | "description" | "icon">;

const getExtensionsCatalog = (page: number = 1) =>
	createResource({
		url: `${hubUrl()}/${HUB_API}.get_catalog`,
		params: { page },
		auto: true,
		cache: [CATALOG_CACHE, page],
		initialData: { extensions: [] as CatalogExtension[] },
		onError: (error: Error) => console.error("Could not load extensions list", error),
	});

/** An extension that is not installed, as its Hub page shows it. It has no permissions and no install date. */
type HubExtension = CatalogExtension & {
	version: string;
	readme?: string;
	source_url?: string;
};

/** The data that `get_extension` returns: the manifest entry and each release. */
type HubExtensionResponse = {
	extension: CatalogExtension & { readme?: string; repository_url?: string };
	releases: { version: string; status: string; published_on: string }[];
};

/** The newest published release. A new install gets this version. */
const latestVersion = (releases: HubExtensionResponse["releases"]) =>
	releases
		.filter((release) => release.status === "Published")
		.sort((a, b) => b.published_on.localeCompare(a.published_on))[0]?.version ?? "";

/**
 * One extension from the Hub, for the page that a user opens before an install.
 *
 * It asks the Hub, not the site, because the site has no record of it yet.
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

/** The permissions that one release asks for. The list has no manifest, so this reads the release. */
const getHubReleasePermissions = async (name: string, version: string): Promise<Permission[]> => {
	const { release } = await createResource({
		url: `${hubUrl()}/${HUB_API}.get_extension_release`,
		params: { extension_name: name, version },
	}).fetch();
	return release.manifest?.permissions ?? [];
};

/**
 * Starts a Hub install. The server returns an "Installing" row and downloads
 * the package in a background job. So this call returns quickly. The row
 * changes to "Ready" or "Failed" on the `builder_extension_install` realtime event.
 *
 * `version` sets the release. The user approved the permissions of that release.
 */
const installFromHub = async (name: string, version: string, permissions: Permission[]) => {
	await call("builder.extensions.hub.install_from_hub", { name, version, permissions });
	await loadExtensions();
};

export {
	canManageExtensions,
	getExtensionSource,
	getExtensionsCatalog,
	getHubExtension,
	getHubReleasePermissions,
	INSTALLATION_DOCTYPE,
	installedExtensions,
	installFromHub,
	loadExtensions,
	setExtensionEnabled,
	setGrantedPermissions,
	uninstallExtension,
	uninstallSummary,
	useInstallationDetails,
	installations,
};

export type { CatalogExtension, HubExtension, InstallationDetails, UninstallSummary, Installation };
