/**
 * The page: the tree that an extension reads, and the page that the editor shows.
 */

import router from "@/router";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { watch } from "vue";
import { getBlockObject } from "@/utils/helpers";
import type { MethodTable } from "../bridge/permissions";
import { fields, refuse, text } from "../bridge/params";

/**
 * A list, because Builder stores a page as a list. Today the list always has
 * one root.
 *
 * With no canvas, the call is refused. It does not return an empty list. So an
 * extension that calls before the editor is ready can tell this from an empty page.
 */
const getBlocks = () => {
	const root = useCanvasStore().activeCanvas?.getRootBlock();
	if (!root) throw refuse("No canvas is open.", "no_canvas");
	return [getBlockObject(root)];
};

const readRouteVariables = (value: unknown) => {
	const isTextMap =
		value !== null &&
		typeof value === "object" &&
		!Array.isArray(value) &&
		Object.values(value).every((entry) => typeof entry === "string");
	if (!isTextMap) throw refuse('"values" must map names to strings.', "invalid_params");
	return value as Record<string, string>;
};

/** A page that does not load in this time is reported, not waited on forever. */
const LOAD_TIMEOUT_MS = 15_000;

/** Resolves when the editor shows `pageName` and has loaded it. */
const waitForPage = (pageName: string) => {
	const pageStore = usePageStore();
	const isLoaded = () => pageStore.activePage?.name === pageName && !pageStore.settingPage;
	if (isLoaded()) return Promise.resolve();
	return new Promise<void>((resolve, reject) => {
		const timer = setTimeout(() => {
			stop();
			reject(refuse(`The page "${pageName}" did not load.`, "invalid_params"));
		}, LOAD_TIMEOUT_MS);
		const stop = watch(isLoaded, (loaded) => {
			if (!loaded) return;
			clearTimeout(timer);
			stop();
			resolve();
		});
	});
};

/**
 * Shows a page in the editor. It answers when the page has loaded, so a
 * following call, such as `page.setRouteVariables`, acts on the new page.
 */
const open = async (params: unknown) => {
	const pageName = text(fields(params).name, "name");
	const pageStore = usePageStore();
	if (pageName !== pageStore.selectedPage) {
		// the user decides to save or discard a component or template, so an extension cannot leave it
		if (useCanvasStore().editingMode !== "page") {
			throw refuse("Close the open component or block template before you open another page.", "refused");
		}
		if (pageStore.activePage && !pageStore.settingPage) await pageStore.waitTillPageIsSaved();
		await router.push({ name: "builder", params: { pageId: pageName } });
	}
	await waitForPage(pageName);
};

/** The preview values of the open page, such as `{ slug: "hello-world" }`. The canvas shows their data. */
const setRouteVariables = async (params: unknown) => {
	const pageStore = usePageStore();
	if (!pageStore.activePage) throw refuse("No page is open.", "no_canvas");
	await pageStore.setRouteVariables(readRouteVariables(fields(params).values));
};

const refreshData = async () => {
	const pageStore = usePageStore();
	if (!pageStore.activePage) throw refuse("No page is open.", "no_canvas");
	// rejects on a failed fetch, so the extension can tell and try again
	await pageStore.loadPageData(pageStore.activePage);
};

export const pageMethods: MethodTable = {
	"page.getBlocks": { needs: null, run: getBlocks },
	// these move the view and the preview only. Neither changes the page
	"page.open": { needs: null, run: open },
	"page.setRouteVariables": { needs: null, run: setRouteVariables },
	"page.refreshData": { needs: null, run: refreshData },
};
