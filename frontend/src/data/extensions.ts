import { devExtension } from "@/extensions/devExtension";
import type { Permission, InstalledExtension } from "frappe-builder-extension-sdk/types";
import { createDocumentResource, createResource, getCachedDocumentResource } from "frappe-ui";
import { computed } from "vue";

const INSTALLATION_DOCTYPE = "Builder Extension";

type InstallationDocument = {
	extension: string;
	label?: string;
	description?: string;
	enabled: boolean | number;
	granted_permissions?: string;
};

/** The Vue instance for the realtime subscription of a document resource. The editor sets it one time. */
let resourceVm: unknown;

const grantedPermissions = (value: string | undefined): Permission[] => {
	if (!value) return [];
	return JSON.parse(value) as Permission[];
};

/**
 * The document of one installation.
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
 * The editor mounts the enabled rows.
 */
const installationsResource = createResource<Installation[]>({
	url: "builder.extensions.installations.get_installations",
	// if this list fails, the editor loses its extensions. The editor itself still works
	onError: (error: Error) => console.error("Could not load installations", error),
});

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
	if (!document || !document.enabled || !row.entry_url) return null;

	return {
		name: row.name,
		label: document.label ?? row.label ?? row.name,
		description: document.description ?? row.description,
		icon: row.icon,
		entryUrl: row.entry_url,
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
	const rows = (await installationsResource.fetch()) ?? [];
	rows.filter((row) => row.enabled && !row.is_development).forEach(loadInstallationDocument);
	return rows;
};

/** One row of the installation list of the site. */
type Installation = {
	name: string;
	/** The name of the document, not of the extension. */
	installation_id: string;
	label?: string;
	description?: string;
	icon?: string;
	enabled: boolean;
	/** The entry URL, with the checksum of the build. Not set for an installation with no checksum. */
	entry_url?: string;
	/** A dev server load made this row. The entry in the browser runs it. The row never runs. */
	is_development?: boolean;
};

export { INSTALLATION_DOCTYPE, installedExtensions, loadExtensions };
