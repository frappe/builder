import { devExtension } from "@/extensions/devExtension";
import type { Permission, InstalledExtension } from "frappe-builder-extension-sdk/types";
import { createResource } from "frappe-ui";
import { computed } from "vue";

const INSTALLATION_DOCTYPE = "Builder Extension";

/**
 * All installations on the site. The editor mounts the enabled rows.
 * Each row has all the data that the editor needs.
 */
const installationsResource = createResource<Installation[]>({
	url: "builder.extensions.installations.get_installations",
	// If the list fails, the editor works without extensions.
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
 * The extensions that the editor runs: the enabled installations and the dev extension.
 * The dev extension replaces an installation with the same name.
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
	/** The granted permissions. The server checks the same list. */
	permissions: Permission[];
	/** The entry URL with the build checksum. Empty if there is no build. */
	entry_url?: string;
	/** True for a dev extension. The editor does not mount this row. */
	is_development?: boolean;
};

export { INSTALLATION_DOCTYPE, installedExtensions, loadExtensions };
