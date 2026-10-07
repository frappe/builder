import { devExtension } from "@/extensions/devExtension";
import type { Permission, InstalledExtension } from "frappe-builder-extension-sdk/types";
import { createResource } from "frappe-ui";
import { computed } from "vue";

const INSTALLATION_DOCTYPE = "Builder Extension";

/**
 * All installations on this site, with the disabled and development installations.
 * The editor mounts the enabled rows.
 *
 * A row has all that the editor needs. A page reader can get the list, but
 * possibly not the installation documents.
 */
const installationsResource = createResource<Installation[]>({
	url: "builder.extensions.installations.get_installations",
	// if this list fails, the editor loses its extensions. The editor itself still works
	onError: (error: Error) => console.error("Could not load installations", error),
});

const toInstalledExtension = (row: Installation): InstalledExtension => ({
	name: row.name,
	label: row.label ?? row.name,
	description: row.description,
	icon: row.icon,
	entryUrl: row.entry_url as string,
	permissions: row.permissions,
});

/**
 * All extensions that this editor runs. These are the installations of the
 * site, and the extension from a dev server in this session. A dev extension
 * replaces the installation with the same name. Two entries would give it two frames.
 *
 * A development record never mounts. It has no files. The entry in the browser runs it.
 */
const installedExtensions = computed<InstalledExtension[]>(() => {
	const installed = (installationsResource.data ?? [])
		.filter((row) => row.enabled && row.entry_url && !row.is_development)
		.map(toInstalledExtension);
	const development = devExtension.value;
	if (!development) return installed;

	return [...installed.filter((extension) => extension.name !== development.name), development];
});

/** Gets the list. Call it after each change. */
const loadExtensions = () => installationsResource.fetch();

/** One row of the installation list of the site. */
type Installation = {
	name: string;
	label?: string;
	description?: string;
	icon?: string;
	enabled: boolean;
	/** What an extension manager allowed. The server gate reads the same list. */
	permissions: Permission[];
	/** The entry URL, with the checksum of the build. Not set for an installation with no checksum. */
	entry_url?: string;
	/** A dev server load made this row. The entry in the browser runs it. The row never runs. */
	is_development?: boolean;
};

export { INSTALLATION_DOCTYPE, installedExtensions, loadExtensions };
