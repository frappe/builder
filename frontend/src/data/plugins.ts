import type { RunnablePlugin } from "@/plugins/context";
import { devPlugin, isDevPlugin } from "@/plugins/devPlugin";
import { loadPlugin, runningPlugins } from "@/plugins/loader";
import { useStorage } from "@vueuse/core";
import { call, createResource, getCachedResource, toast } from "frappe-ui";
import { computed, reactive, shallowRef } from "vue";

const METHOD = "builder.plugins.installations";
const HUB_API = "api/method/builder_hub.plugins.api";
const CATALOG_CACHE = "plugins-catalog";
/** The Hub lists the releases at or below this protocol. Keep in step with `builder/plugins/constants.py`. */
const PROTOCOL_VERSION = 1;

/** A choice of this user in this browser. It is not an access control, so the server does not read it. */
const pluginsDisabled = useStorage("builderPluginsDisabled", false);

/** The server names the Hub, because only a manager can read Builder Settings. */
const getHubMethodUrl = async (method: string) =>
	`${await call("builder.plugins.hub.get_hub_url")}/${HUB_API}.${method}`;

/**
 * A GET to the Hub with no cookies and no headers. `frappeRequest` sends the
 * CSRF token of this site, and the Hub must never get it.
 */
const hubRequest = async (method: string, params: Record<string, string | number>) => {
	const query = new URLSearchParams(Object.entries(params).map(([key, value]) => [key, String(value)]));
	const response = await fetch(`${await getHubMethodUrl(method)}?${query}`, { credentials: "omit" });
	if (!response.ok) throw new Error(`The Builder Hub returned an error (${response.status}).`);
	return (await response.json()).message;
};

/** One row of the installation list of the site. */
type Installation = {
	/** The plugin, as publisher/name. */
	name: string;
	/** The name of the document, not of the plugin. */
	installation_id: string;
	label?: string;
	description?: string;
	icon?: string;
	version: string;
	/** Where the files came from. */
	source: "Hub" | "App" | "Development";
	/** The Builder Hub that it came from, when `source` is "Hub". */
	hub_url?: string;
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
	/** The code repository. Only a Hub listing has it. */
	repository_url?: string;
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
	// if this list fails, the editor loses its plugins. The editor itself still works
	onError: (error: Error) => console.error("Could not load installations", error),
});

/** True if this user can install, turn on, turn off or remove plugins. The server also checks each call. */
const managerResource = createResource<boolean>({
	url: `${METHOD}.can_manage_plugins`,
	onError: (error: Error) => console.error("Could not check plugin access", error),
});

const canManagePlugins = computed(() => Boolean(managerResource.data));

/** Gets the list. Call it after each change. */
const reloadInstallations = () => {
	if (managerResource.data === null) void managerResource.fetch();
	return installationsResource.fetch();
};

const isRunnable = (row: Installation) =>
	row.enabled && row.entry_url && !row.is_development && (row.install_state ?? "Ready") === "Ready";

const toRunnable = (row: Installation): RunnablePlugin => ({
	name: row.name,
	label: row.label ?? row.name,
	version: row.version,
	entryUrl: row.entry_url as string,
});

/** The installed plugins this editor loads at startup. A dev plugin loads later, from its dialog. */
const getStartupPlugins = async (): Promise<RunnablePlugin[]> => {
	if (pluginsDisabled.value) return [];
	const rows = (await reloadInstallations()) ?? [];
	return rows.filter(isRunnable).map(toRunnable);
};

/** The install job writes the package icon last. So an Installing or Failed row uses the icon from the Hub catalog. */
const withCatalogIcon = (row: Installation): Installation => {
	if (row.icon || !row.install_state || row.install_state === "Ready") return row;
	const catalog: CatalogPlugin[] = getCachedResource([CATALOG_CACHE, 1])?.data?.plugins ?? [];
	return { ...row, icon: catalog.find((plugin) => plugin.name === row.name)?.icon };
};

/** A running dev plugin shows the data from its dev server. It is always enabled. */
const withDevelopment = (row: Installation): Installation => {
	const development = devPlugin.value;
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
		if (isDevPlugin(row)) devInstallation.push(withDevelopment(withCatalogIcon(row)));
		else if (!row.is_development) others.push(withCatalogIcon(row));
	}
	return [...devInstallation, ...others];
});

const findInstallation = (plugin: string) =>
	installations.value.find((installation) => installation.name === plugin);

/** The data that only a running dev server has. */
const applyDevelopmentDetails = (details: InstallationDetails): InstallationDetails => {
	const development = devPlugin.value;
	if (!development || development.name !== details.name) return details;
	return { ...details, readme: development.readme, development_server: development.serverOrigin };
};

/** One installation. The server sends the readme, because a page reader may not read the installation. */
const useInstallationDetails = (plugin: string) => {
	const stored = shallowRef<{ installed_on?: string; readme?: string } | null>(null);

	const reload = async () => {
		if (!findInstallation(plugin)) return;
		const { is_updating, ...rest } = (await call(`${METHOD}.get_installation_details`, {
			plugin,
		})) as { installed_on: string; readme?: string; is_updating: boolean };
		stored.value = rest;
		// the job ended, but its realtime message did not arrive
		if (!is_updating && updatingPlugins.delete(plugin)) await reloadInstallations();
	};

	const details = computed<InstallationDetails | null>(() => {
		const installation = findInstallation(plugin);
		if (!installation || !stored.value) return null;
		return applyDevelopmentDetails({
			...installation,
			...stored.value,
			installed_on: stored.value.installed_on ?? "",
		});
	});

	return { details, reload };
};

/** A running Vue plugin cannot leave the app, so a change to what runs waits for a reload. */
const promptReload = (message: string) =>
	toast.success(message, {
		description: "Reload the editor to apply it.",
		duration: 10000,
		action: { label: "Reload", onClick: () => window.location.reload() },
	});

const setPluginEnabled = async (plugin: string, enabled: boolean) => {
	await call(`${METHOD}.set_plugin_enabled`, { plugin, enabled });
	await reloadInstallations();
	if (enabled && !runningPlugins.has(plugin)) await loadInstalled(plugin);
	else promptReload(enabled ? "Plugin enabled" : "Plugin disabled");
};

const uninstallPlugin = async (plugin: string) => {
	const wasRunning = runningPlugins.has(plugin);
	await call(`${METHOD}.uninstall_plugin`, { plugin });
	await reloadInstallations();
	if (wasRunning) promptReload("Plugin uninstalled");
};

/** Loads one installed plugin while the editor runs. */
const loadInstalled = async (plugin: string) => {
	const row = (installationsResource.data ?? []).find((installation) => installation.name === plugin);
	if (!row || !isRunnable(row) || pluginsDisabled.value) return;
	try {
		await loadPlugin(toRunnable(row));
	} catch (error) {
		toast.error(`${row.label ?? plugin} could not load: ${(error as Error).message}`);
	}
};

type CatalogPlugin = Pick<Installation, "name" | "label" | "description" | "icon">;

const getPluginsCatalog = (page: number = 1) =>
	createResource({
		url: "get_catalog",
		resourceFetcher: (options: { url: string; params: Record<string, number> }) =>
			hubRequest(options.url, options.params),
		params: { page, protocol_version: PROTOCOL_VERSION },
		auto: true,
		cache: [CATALOG_CACHE, page],
		initialData: { plugins: [] as CatalogPlugin[] },
		onError: (error: Error) => console.error("Could not load plugins list", error),
	});

/** A plugin that is not installed, as its Hub page shows it. */
type HubPlugin = CatalogPlugin & {
	version: string;
	readme?: string;
	repository_url?: string;
};

/** The data that `get_plugin` returns: the manifest entry and each release. */
type HubPluginResponse = {
	plugin: CatalogPlugin & { readme?: string; repository_url?: string };
	releases: { version: string; status: string; published_on: string }[];
};

/** The newest published release. A new install gets this version. */
const latestVersion = (releases: HubPluginResponse["releases"]) =>
	releases
		.filter((release) => release.status === "Published")
		.sort((a, b) => b.published_on.localeCompare(a.published_on))[0]?.version ?? "";

/** One plugin from the Hub. It asks the Hub, not the site, because the site has no record of it yet. */
const getHubPlugin = async (name: string): Promise<HubPlugin> => {
	const { plugin, releases }: HubPluginResponse = await hubRequest("get_plugin", {
		name,
		protocol_version: PROTOCOL_VERSION,
	});

	return {
		name: plugin.name,
		label: plugin.label,
		description: plugin.description,
		icon: plugin.icon,
		readme: plugin.readme,
		repository_url: plugin.repository_url,
		version: latestVersion(releases),
	};
};

/**
 * Starts a Hub install. The server returns an "Installing" row and downloads
 * the package in a background job. The row changes to "Ready" or "Failed" on
 * the `builder_plugin_install` realtime event.
 */
const installFromHub = async (name: string, version: string) => {
	await call("builder.plugins.hub.install_from_hub", { name, version });
	await reloadInstallations();
};

/** A newer Hub release of an installed plugin. */
type PluginUpdate = { version: string };

const getPluginUpdate = (plugin: string) =>
	call("builder.plugins.updates.get_update", { plugin }) as Promise<PluginUpdate | null>;

/** The plugins with an update job running. It lives here, so it outlasts the details page. */
const updatingPlugins = reactive(new Set<string>());

/** The installed release runs until the job ends. The job then sends `builder_plugin_update`. */
const updateFromHub = async (plugin: string, version: string) => {
	// before the call: a fast job can send its end before the response arrives
	updatingPlugins.add(plugin);
	try {
		await call("builder.plugins.updates.update_from_hub", { plugin, version });
	} catch (error) {
		updatingPlugins.delete(plugin);
		throw error;
	}
};

const labelOf = (plugin: string) => findInstallation(plugin)?.label ?? plugin;

const finishInstall = async ({ plugin, state }: { plugin: string; state: "Ready" | "Failed" }) => {
	await reloadInstallations();
	if (state === "Failed") return toast.error(`Could not install ${labelOf(plugin)}`);
	toast.success(`Installed ${labelOf(plugin)}`);
	await loadInstalled(plugin);
};

const finishUpdate = async ({ plugin, error }: { plugin: string; error?: string | null }) => {
	updatingPlugins.delete(plugin);
	await reloadInstallations();
	if (error) toast.error(`${labelOf(plugin)} could not update: ${error}`);
	else if (runningPlugins.has(plugin)) promptReload(`${labelOf(plugin)} is up to date`);
	else toast.success(`${labelOf(plugin)} is up to date`);
};

/** The install and update jobs end in a background worker. These listeners stay for the whole editor session. */
const listenForPluginJobs = (realtime: { on: (event: string, handler: (data: any) => void) => void }) => {
	realtime.on("builder_plugin_install", finishInstall);
	realtime.on("builder_plugin_update", finishUpdate);
};

export {
	canManagePlugins,
	pluginsDisabled,
	getPluginsCatalog,
	getPluginUpdate,
	getHubPlugin,
	getStartupPlugins,
	installations,
	installFromHub,
	listenForPluginJobs,
	promptReload,
	reloadInstallations,
	setPluginEnabled,
	uninstallPlugin,
	updateFromHub,
	updatingPlugins,
	useInstallationDetails,
};

export type { CatalogPlugin, PluginUpdate, HubPlugin, Installation, InstallationDetails };
