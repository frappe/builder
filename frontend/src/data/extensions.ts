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
	granted_permissions?: string;
	/** The rest is unread by the mount list, and read only by the details panel. */
	version?: string;
	source_url?: string;
	install_state?: "Installing" | "Ready" | "Failed";
	install_error?: string;
	installed_on?: string;
	readme?: string;
	requested_permissions?: string;
};

/** The Vue instance a document resource ties its realtime subscription to. Set once, from the editor. */
let resourceVm: unknown;

const grantedPermissions = (value: string | undefined): Permission[] => {
	if (!value) return [];
	return JSON.parse(value) as Permission[];
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
 * Every installation on this site, the disabled and development ones included.
 *
 * The editor mounts the enabled rows, and the panel shows them all. One list
 * means one fetch to refresh after a change, so the two never disagree.
 */
const installationsResource = createResource<Installation[]>({
	url: "builder.extensions.installations.get_installations",
	// losing this list costs the editor its extensions, never the editor itself
	onError: (error: Error) => console.error("Could not load installations", error),
});

/**
 * Whether this user may install, turn on or off, grant or uninstall. The panel
 * hides those controls without it, and the server checks again on every call.
 */
const managerResource = createResource<boolean>({
	url: "builder.extensions.installations.can_manage_extensions",
	onError: (error: Error) => console.error("Could not check extension access", error),
});

const canManageExtensions = computed(() => Boolean(managerResource.data));

/**
 * Fetch one installation's document into that shared cache.
 *
 * Read it back with `getCachedDocumentResource`, never held here: `toInstalledExtension`
 * only reads that cache, so a fetch never happens as a side effect of a computed.
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
 * Every extension this editor runs: the site's installations, plus the one loaded from a
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
	if (managerResource.data === null) void managerResource.fetch();
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
type Installation = {
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

type InstallationDetails = Installation & {
	installed_on: string;
	readme?: string;
	requested_permissions: Permission[];
	granted_permissions: Permission[];
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
const withCatalogIcon = (row: Installation): Installation => {
	if (row.icon || !row.install_state || row.install_state === "Ready") return row;
	const catalog: CatalogExtension[] = getCachedResource([CATALOG_CACHE, 1])?.data?.extensions ?? [];
	return { ...row, icon: catalog.find((extension) => extension.name === row.name)?.icon };
};

/** A running dev extension shows what its dev server serves, and is always enabled. */
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
 * What the panel manages, which is not what the editor mounts.
 *
 * `installedExtensions` drops a disabled installation, because a frame must not
 * run for one. The panel keeps it, because turning it back on is the point.
 *
 * A development record that no dev server runs this session is one a closed tab
 * failed to remove, so the panel hides it.
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
 * One installation, with the dev server standing in for what it owns.
 *
 * A development installation is real, so the record answers for the permissions
 * it granted and the install date. What the dev server shows a user comes from
 * the dev server, which is the copy running right now.
 *
 * Composed from what the mount list and the panel's own list already fetch,
 * rather than a details call of its own: the document carries the readme and the
 * raw permission lists, and `findInstallation` carries the icon and the install
 * state.
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

/** What the site keeps when a manager removes an extension. */
type UninstallSummary = {
	resources: { resource_type: string; count: number }[];
	tokens: number;
};

/**
 * Every write below reloads the list, so no caller can leave the panel showing
 * one answer and the editor running another.
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
	// the editor runs the browser's own entry for a dev extension, not its record,
	// so the new grant has to reach that entry too
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

/** A not-installed extension as its hub page describes it. No permissions, no install date. */
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
const getHubReleasePermissions = async (name: string, version: string): Promise<Permission[]> => {
	const { release } = await createResource({
		url: `${hubUrl()}/${HUB_API}.get_extension_release`,
		params: { extension_name: name, version },
	}).fetch();
	return release.manifest?.permissions ?? [];
};

/**
 * Start a Hub install. The server answers with an "Installing" row and runs the
 * download in a background job, so this resolves fast. The row flips to "Ready"
 * or "Failed" on the `builder_extension_install` realtime event.
 *
 * `version` pins the release whose permissions the user answered for.
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
