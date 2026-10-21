import type { RunnableExtension } from "@/extensions/context";
import { devExtension, isDevExtension } from "@/extensions/devExtension";
import { loadExtension, runningExtensions } from "@/extensions/loader";
import { useStorage } from "@vueuse/core";
import { call, createResource, frappeRequest, getCachedResource, toast } from "frappe-ui";
import { computed, reactive, shallowRef } from "vue";

const METHOD = "builder.extensions.installations";
const HUB_API = "api/method/builder_hub.extensions.api";
const CATALOG_CACHE = "extensions-catalog";

/** A choice of this user in this browser. It is not an access control, so the server does not read it. */
const extensionsDisabled = useStorage("builderExtensionsDisabled", false);

/** The server names the Hub, because only a manager can read Builder Settings. */
const getHubMethodUrl = async (method: string) =>
	`${await call("builder.extensions.hub.get_hub_url")}/${HUB_API}.${method}`;

/** One row of the installation list of the site. */
type Installation = {
	/** The extension, as publisher/name. */
	name: string;
	/** The name of the document, not of the extension. */
	installation_id: string;
	label?: string;
	description?: string;
	icon?: string;
	version: string;
	/** The Builder Hub that it came from. */
	source_url: string;
	enabled: boolean;
	/** A Hub install is "Installing" until its background job ends. Then it is "Ready" or "Failed". */
	install_state?: "Installing" | "Ready" | "Failed";
	/** Why the last Hub install failed. The panel shows it with a Retry button. */
	install_error?: string;
	/** The entry URL, with the checksum of the build. */
	entry_url?: string;
	/** A dev server load made this row. The browser loads its entry from the dev server. */
	is_development?: boolean;
};

type InstallationDetails = Installation & {
	installed_on: string;
	readme?: string;
	development_server?: string;
};

/**
 * All installations on this site, with the disabled and development ones.
 *
 * The editor loads the enabled rows, and the panel shows all rows. With one
 * list, one request updates both after a change.
 */
const installationsResource = createResource<Installation[]>({
	url: `${METHOD}.get_installations`,
	// if this list fails, the editor loses its extensions. The editor itself still works
	onError: (error: Error) => console.error("Could not load installations", error),
});

/** True if this user can install, turn on, turn off or remove extensions. The server also checks each call. */
const managerResource = createResource<boolean>({
	url: `${METHOD}.can_manage_extensions`,
	onError: (error: Error) => console.error("Could not check extension access", error),
});

const canManageExtensions = computed(() => Boolean(managerResource.data));

/** Gets the list. Call it after each change. */
const reloadInstallations = () => {
	if (managerResource.data === null) void managerResource.fetch();
	return installationsResource.fetch();
};

const isRunnable = (row: Installation) =>
	row.enabled && row.entry_url && !row.is_development && (row.install_state ?? "Ready") === "Ready";

const toRunnable = (row: Installation): RunnableExtension => ({
	name: row.name,
	label: row.label ?? row.name,
	version: row.version,
	entryUrl: row.entry_url as string,
});

/** The installed extensions this editor loads at startup. A dev extension loads later, from its dialog. */
const getStartupExtensions = async (): Promise<RunnableExtension[]> => {
	if (extensionsDisabled.value) return [];
	const rows = (await reloadInstallations()) ?? [];
	return rows.filter(isRunnable).map(toRunnable);
};

/** The install job writes the package icon last. So an Installing or Failed row uses the icon from the Hub catalog. */
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
 * The rows that the panel manages.
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

/** The data that only a running dev server has. */
const applyDevelopmentDetails = (details: InstallationDetails): InstallationDetails => {
	const development = devExtension.value;
	if (!development || development.name !== details.name) return details;
	return { ...details, readme: development.readme, development_server: development.serverOrigin };
};

/** One installation. The server sends the readme, because a page reader may not read the installation. */
const useInstallationDetails = (extension: string) => {
	const stored = shallowRef<{ installed_on?: string; readme?: string } | null>(null);

	const reload = async () => {
		if (!findInstallation(extension)) return;
		stored.value = await call(`${METHOD}.get_installation_details`, { extension });
	};

	const details = computed<InstallationDetails | null>(() => {
		const installation = findInstallation(extension);
		if (!installation || !stored.value) return null;
		return applyDevelopmentDetails({
			...installation,
			...stored.value,
			installed_on: stored.value.installed_on ?? "",
		});
	});

	return { details, reload };
};

/** A running plugin cannot leave the app, so a change to what runs waits for a reload. */
const promptReload = (message: string) =>
	toast.success(message, {
		description: "Reload the editor to apply it.",
		duration: 10000,
		action: { label: "Reload", onClick: () => window.location.reload() },
	});

const setExtensionEnabled = async (extension: string, enabled: boolean) => {
	await call(`${METHOD}.set_extension_enabled`, { extension, enabled });
	await reloadInstallations();
	if (enabled && !runningExtensions.has(extension)) await loadInstalled(extension);
	else promptReload(enabled ? "Extension enabled" : "Extension disabled");
};

const uninstallExtension = async (extension: string) => {
	const wasRunning = runningExtensions.has(extension);
	await call(`${METHOD}.uninstall_extension`, { extension });
	await reloadInstallations();
	if (wasRunning) promptReload("Extension uninstalled");
};

/** Loads one installed extension while the editor runs. */
const loadInstalled = async (extension: string) => {
	const row = (installationsResource.data ?? []).find((installation) => installation.name === extension);
	if (!row || !isRunnable(row) || extensionsDisabled.value) return;
	try {
		await loadExtension(toRunnable(row));
	} catch (error) {
		toast.error(`${row.label ?? extension} could not load: ${(error as Error).message}`);
	}
};

type CatalogExtension = Pick<Installation, "name" | "label" | "description" | "icon">;

const getExtensionsCatalog = (page: number = 1) =>
	createResource({
		url: "get_catalog",
		// the Hub URL comes from the server, so it is known only when the fetch starts
		resourceFetcher: async (options: { url: string }) =>
			frappeRequest({ ...options, url: await getHubMethodUrl(options.url) }),
		params: { page },
		auto: true,
		cache: [CATALOG_CACHE, page],
		initialData: { extensions: [] as CatalogExtension[] },
		onError: (error: Error) => console.error("Could not load extensions list", error),
	});

/** An extension that is not installed, as its Hub page shows it. */
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

/** One extension from the Hub. It asks the Hub, not the site, because the site has no record of it yet. */
const getHubExtension = async (name: string): Promise<HubExtension> => {
	const { extension, releases }: HubExtensionResponse = await createResource({
		url: await getHubMethodUrl("get_extension"),
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
 * Starts a Hub install. The server returns an "Installing" row and downloads
 * the package in a background job. The row changes to "Ready" or "Failed" on
 * the `builder_extension_install` realtime event.
 */
const installFromHub = async (name: string, version: string) => {
	await call("builder.extensions.hub.install_from_hub", { name, version });
	await reloadInstallations();
};

/** A newer Hub release of an installed extension. */
type ExtensionUpdate = { version: string };

const getExtensionUpdate = (extension: string) =>
	call("builder.extensions.updates.get_update", { extension }) as Promise<ExtensionUpdate | null>;

/** The extensions with an update job running. It lives here, so it outlasts the details page. */
const updatingExtensions = reactive(new Set<string>());

/** The installed release runs until the job ends. The job then sends `builder_extension_update`. */
const updateFromHub = async (extension: string, version: string) => {
	// before the call: a fast job can send its end before the response arrives
	updatingExtensions.add(extension);
	try {
		await call("builder.extensions.updates.update_from_hub", { extension, version });
	} catch (error) {
		updatingExtensions.delete(extension);
		throw error;
	}
};

const labelOf = (extension: string) => findInstallation(extension)?.label ?? extension;

const finishInstall = async ({ extension, state }: { extension: string; state: "Ready" | "Failed" }) => {
	await reloadInstallations();
	if (state === "Failed") return toast.error(`Could not install ${labelOf(extension)}`);
	toast.success(`Installed ${labelOf(extension)}`);
	await loadInstalled(extension);
};

const finishUpdate = async ({ extension, error }: { extension: string; error?: string | null }) => {
	updatingExtensions.delete(extension);
	await reloadInstallations();
	if (error) toast.error(`${labelOf(extension)} could not update: ${error}`);
	else if (runningExtensions.has(extension)) promptReload(`${labelOf(extension)} is up to date`);
	else toast.success(`${labelOf(extension)} is up to date`);
};

/** The install and update jobs end in a background worker. These listeners stay for the whole editor session. */
const listenForExtensionJobs = (realtime: { on: (event: string, handler: (data: any) => void) => void }) => {
	realtime.on("builder_extension_install", finishInstall);
	realtime.on("builder_extension_update", finishUpdate);
};

export {
	canManageExtensions,
	extensionsDisabled,
	getExtensionsCatalog,
	getExtensionUpdate,
	getHubExtension,
	getStartupExtensions,
	installations,
	installFromHub,
	listenForExtensionJobs,
	promptReload,
	reloadInstallations,
	setExtensionEnabled,
	uninstallExtension,
	updateFromHub,
	updatingExtensions,
	useInstallationDetails,
};

export type { CatalogExtension, ExtensionUpdate, HubExtension, Installation, InstallationDetails };
