/**
 * The editor keeps copies of some Builder records. A `data.*` write changes
 * only the record, so this table reloads the copy that the write made stale.
 * The stores stay the owners of their copies. This file only tells them to reload.
 */

import { allWebPages, linkablePages } from "@/data/allWebPages";
import builderBlockTemplate from "@/data/builderBlockTemplate";
import { builderSettings } from "@/data/builderSettings";
import builderTokens from "@/data/builderToken";
import userFont from "@/data/userFonts";
import { webPages } from "@/data/webPage";
import useBlockTemplateStore from "@/stores/blockTemplateStore";
import useComponentStore from "@/stores/componentStore";
import usePageStore from "@/stores/pageStore";

export type Write = "insert" | "update" | "delete";

type Refresh = (name: string, write: Write) => unknown;

const refreshPage: Refresh = (name, write) => {
	// an update can rename a route too, but the lists only show it after a reload
	if (write !== "update") [webPages, allWebPages, linkablePages].forEach((list) => list.reload());
	const pageStore = usePageStore();
	if (name === pageStore.activePage?.name) return pageStore.refreshActivePage();
};

/** A new script is not on the page until a `Builder Page` write links it. That write refreshes it. */
const refreshScript: Refresh = (name) => {
	const pageStore = usePageStore();
	const isOnPage = pageStore.activePage?.client_scripts?.some((link) => link.builder_script === name);
	if (isOnPage) return pageStore.refreshActivePage();
};

const refreshBlockTemplate: Refresh = (name) => {
	useBlockTemplateStore().blockTemplateMap.delete(name);
	return builderBlockTemplate.reload();
};

const REFRESH: Record<string, Refresh> = {
	"Builder Page": refreshPage,
	"Builder Client Script": refreshScript,
	"Builder Component": (name, write) => useComponentStore().refreshComponent(name, write === "delete"),
	"Builder Token": () => builderTokens.reload(),
	"User Font": () => userFont.reload(),
	"Block Template": refreshBlockTemplate,
	"Builder Settings": () => builderSettings.reload(),
};

/**
 * The write already succeeded, so a failed reload must not fail the call. A
 * retry would write a second time. The editor shows the old copy until the next load.
 */
export const refreshEditor = async (doctype: string, name: string, write: Write) => {
	try {
		await REFRESH[doctype]?.(name, write);
	} catch (error) {
		console.error(`The editor could not reload ${doctype} "${name}" after an extension wrote it.`, error);
	}
};
