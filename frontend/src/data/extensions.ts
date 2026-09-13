import { devExtension, setDevCapabilities } from "@/extensions/devExtension";
import type { Capability, InstalledExtension } from "frappe-builder-extension-sdk/types";
import { call, createResource } from "frappe-ui";
import { computed } from "vue";
import { builderSettings } from "@/data/builderSettings";

const METHOD = "builder.extensions.installations";

const HUB_API = "api/method/builder_hub.extensions.api";

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

const extensionsResource = createResource({
	url: "builder.extensions.registry.get_enabled_extensions",
	// losing this list costs the editor its extensions, never the editor itself
	onError: (error: Error) => console.error("Could not load extensions", error),
});

/**
 * Every extension this user runs: their installations, plus the one loaded from a
 * dev server this session. A dev extension replaces the installation of the same
 * name, because two entries would give it two frames.
 */
export const installedExtensions = computed<InstalledExtension[]>(() => {
	const installed: InstalledExtension[] = extensionsResource.data ?? [];
	const development = devExtension.value;
	if (!development) return installed;

	return [...installed.filter((extension) => extension.name !== development.name), development];
});

export const loadExtensions = () => extensionsResource.fetch();

/**
 * The built entry of one installation, which a frame runs from a Blob.
 *
 * The editor reads it, not the frame, because a frame sends no session. Fetched
 * once and shared by the five frames that mount one extension. The checksum joins
 * the key, so a rebuild is fetched again. A failed fetch is dropped, so a
 * reloaded frame asks rather than replaying the error.
 */
const sources = new Map<string, Promise<string>>();

export const extensionSource = (extension: InstalledExtension): Promise<string> => {
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
export type UserInstallation = {
	name: string;
	label?: string;
	description?: string;
	icon?: string;
	/** Empty for the dev extension, which runs from a server rather than a release. */
	version: string;
	/** The Builder Hub it came from. Empty for an extension installed from a directory. */
	source_url: string;
	enabled: boolean;
	/** A Hub install is "Installing" until its background job lands, then "Ready" or "Failed". */
	install_state?: "Installing" | "Ready" | "Failed";
	/** Why the last Hub install failed, shown with a Retry. */
	install_error?: string;
};

/** One doctype this user answered for, as `Builder Extension Grant` holds it. */
export type ExtensionGrant = {
	document_type: string;
	can_read: number;
	can_write: number;
	can_delete: number;
	denied: number;
};

export type InstallationDetails = UserInstallation & {
	installed_on: string;
	readme?: string;
	requested_capabilities: Capability[];
	granted_capabilities: Capability[];
	grants: ExtensionGrant[];
	is_development?: boolean;
	development_server?: string;
};

const applyDevelopmentDetails = (details: InstallationDetails): InstallationDetails => {
	const development = devExtension.value;
	if (!development || development.name !== details.name) return details;

	return {
		...details,
		label: development.label,
		description: development.description,
		icon: development.icon,
		version: development.version,
		readme: development.readme,
		is_development: true,
		development_server: development.serverOrigin,
	};
};

/**
 * What the panel manages, which is not what the editor mounts.
 *
 * `installedExtensions` drops a disabled installation, because a frame must not
 * run for one. The panel keeps it, because turning it back on is the point.
 */
const installationsResource = createResource({
	url: "builder.extensions.installations.get_user_installations",
	onError: (error: Error) => console.error("Could not load installations", error),
});

export const userInstallations = computed<UserInstallation[]>(() => {
	const installed: UserInstallation[] = installationsResource.data ?? [];
	const development = devExtension.value;
	if (!development) return installed;

	// The server leaves a development installation out, so the browser's own entry
	// is the only row for it, exactly as it is in the mount list.
	return [
		...installed.filter((row) => row.name !== development.name),
		{
			name: development.name,
			label: development.label,
			description: development.description,
			icon: development.icon,
			version: development.version,
			source_url: "",
			enabled: true,
		},
	];
});

export const loadUserInstallations = () => installationsResource.fetch();

/**
 * Both lists, after a change to an installation.
 *
 * Enabling, disabling and uninstalling all move an extension between the two, and
 * a grant change remounts its frames, so neither list may be refreshed alone.
 */
export const reloadExtensions = async () => {
	await Promise.all([extensionsResource.fetch(), installationsResource.fetch()]);
};

/**
 * One installation, with the dev server standing in for what it owns.
 *
 * A development installation is real, so the record answers for the capabilities
 * it granted, the doctype grants and the install date. What the dev server shows
 * a user comes from the dev server, which is the copy running right now.
 */

export const getInstallationDetails = (extension: string) =>
	createResource<InstallationDetails>({
		url: `${METHOD}.get_installation`,
		params: { extension },
		transform: applyDevelopmentDetails,
		onError: (error: Error) => console.error("Could not load installation details", error),
	});

/**
 * The answer that stands for one doctype, answering with the grants after it.
 *
 * Allowing nothing drops the answer, so the extension asks again. Denying is
 * what stops it asking, and allowing nothing is the only way back from that.
 */
export const setExtensionGrant = (extension: string, doctype: string, access: string[], denied = false) =>
	call(`${METHOD}.set_extension_grant`, { extension, doctype, access, denied }) as Promise<ExtensionGrant[]>;

/** What the site keeps when a user removes an extension. */
export type UninstallSummary = {
	resources: { resource_type: string; count: number }[];
	tokens: number;
	other_users: number;
};

/**
 * Every write below reloads both lists, so no caller can leave the panel showing
 * one answer and the editor running another.
 */
export const setExtensionEnabled = async (extension: string, enabled: boolean) => {
	await call(`${METHOD}.set_extension_enabled`, { extension, enabled });
	await reloadExtensions();
};

export const setGrantedCapabilities = async (extension: string, capabilities: Capability[]) => {
	const granted = (await call(`${METHOD}.set_granted_capabilities`, {
		extension,
		capabilities,
	})) as Capability[];
	// the mount list leaves a development installation out, so the reload below
	// cannot carry the new grant to the entry the browser gate reads
	setDevCapabilities(extension, granted);
	await reloadExtensions();
	return granted;
};

export const uninstallSummary = (extension: string) =>
	call(`${METHOD}.get_uninstall_summary`, { extension }) as Promise<UninstallSummary>;

export const uninstallExtension = async (extension: string) => {
	await call(`${METHOD}.uninstall_extension`, { extension });
	await reloadExtensions();
};

export type CatalogExtension = Pick<UserInstallation, "name" | "label" | "description" | "icon">;

/** One row the Extensions panel opened, and whether this user has it installed. */
export type SelectedExtension = {
	name: string;
	isInstalled: boolean;
};

export const getExtensionsCatalog = (page: number = 1) =>
	createResource({
		url: `${hubUrl()}/${HUB_API}.get_catalog`,
		params: { page },
		auto: true,
		initialData: { extensions: [] as CatalogExtension[] },
		onError: (error: Error) => console.error("Could not load extensions list", error),
	});

/** A not-installed extension as its hub page describes it. No grants, no install date. */
export type HubExtension = CatalogExtension & {
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
export const getHubExtension = async (name: string): Promise<HubExtension> => {
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

/**
 * Start a Hub install. The server answers with an "Installing" row and runs the
 * download in a background job, so this resolves fast. The row flips to "Ready"
 * or "Failed" on the `builder_extension_install` realtime event.
 */
export const installFromHub = async (name: string) => {
	await call("builder.extensions.hub.install_from_hub", { name });
	await reloadExtensions();
};
