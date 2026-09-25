import builderProjectFolder from "@/data/builderProjectFolder";
import { builderSettings } from "@/data/builderSettings";
import router from "@/router";
import { useDashboardState } from "@/composables/useDashboardState";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { __ } from "@/translation";
import { BuilderPage, BuilderProjectFolder } from "@/types/doctypes";
import { webPages } from "@/data/webPage";
import { confirm, openInDesk } from "@/utils/helpers";
import { createListResource, createResource, dialog, toast } from "frappe-ui";
import { ref } from "vue";

export const FOLDER_PAGE_LIMIT = 500;

// the pages of one folder, the one the open page lives in; PagesSection points it at that folder
export const folderPages = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: ["name", "page_name", "page_title", "route", "project_folder", "published", "staging", "is_standard"],
	filters: { is_template: 0, project_folder: "" },
	// creation order keeps a template's pages in the order the template lists them
	orderBy: "creation asc",
	pageLength: FOLDER_PAGE_LIMIT,
});

// page counts per folder for the dashboard sidebar, one grouped query instead of loading every page
export const folderCounts = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: ["project_folder", { COUNT: "*", as: "page_count" }],
	filters: { is_template: 0, project_folder: ["is", "set"] },
	groupBy: "project_folder",
	pageLength: 1000,
	auto: true,
});

export const folderPageCount = (folder: string): number =>
	folderCounts.data?.find((row: { project_folder: string }) => row.project_folder === folder)?.page_count ?? 0;

// bumped after any page change so every page list refreshes from the server
export const pagesVersion = ref(0);

export function notifyPagesChanged({ reloadDashboard = true } = {}) {
	pagesVersion.value++;
	folderCounts.reload();
	if (reloadDashboard) webPages.reload();
}

const isOpen = (page: BuilderPage) => page.name === usePageStore().activePage?.name;

export async function openPage(page: BuilderPage) {
	if (isOpen(page)) return;
	const pageStore = usePageStore();
	// a page switch mid-debounce would save the old edits onto whichever page is loaded by then
	if (pageStore.savingPage) await pageStore.waitTillPageIsSaved();
	router.push({ name: "builder", params: { pageId: page.name } });
}

// template titles repeat the site name ("Rooms · Tide House"), the folder already says it
export const shortTitle = (page: BuilderPage) =>
	(page.page_title || page.page_name || "").split(/\s+[·|—]\s+/)[0];

// the site homepage when the folder holds it, else the page the folder was started with
async function openFolder(folder: string) {
	const homeRoute = builderSettings.doc?.home_page;
	const [home] = homeRoute ? await firstPageIn(folder, { route: homeRoute }) : [];
	const page = home ?? (await firstPageIn(folder))[0];
	if (!page) return createPageIn(folder);
	useBuilderStore().leftPanelActiveTab = "Layers";
	router.push({ name: "builder", params: { pageId: page.name } });
}

export function createPageIn(folder: string) {
	router.push({ name: "builder", params: { pageId: "new" }, query: folder ? { folder } : {} });
}

// the open page saves through the page store so its unsaved state stays consistent
async function setPageValue(page: BuilderPage, field: keyof BuilderPage, value: string) {
	if (isOpen(page)) {
		// the list refreshes below, so wait for the save or it comes back with the old value
		await usePageStore().updateActivePage(field, value);
	} else {
		await createResource({ url: "frappe.client.set_value" }).submit({
			doctype: "Builder Page",
			name: page.name,
			fieldname: field,
			value,
		});
	}
	notifyPagesChanged();
}

const movePage = (page: BuilderPage, folder: string) => {
	if ((page.project_folder || "") !== folder) setPageValue(page, "project_folder", folder);
};

function renamePage(page: BuilderPage) {
	dialog.prompt({
		title: __("Rename Page"),
		size: "sm",
		confirmLabel: __("Rename"),
		fields: [{ name: "title", label: __("Title"), required: true, defaultValue: page.page_title || "" }],
		onConfirm: ({ values }) => setPageValue(page, "page_title", values.title),
	});
}

function firstPageIn(folder: string, extraFilters = {}): Promise<BuilderPage[]> {
	return createResource({ url: "frappe.client.get_list" }).submit({
		doctype: "Builder Page",
		fields: ["name"],
		filters: { is_template: 0, project_folder: folder, ...extraFilters },
		order_by: "creation asc",
		limit_page_length: 1,
	});
}

// the page after it in its folder's loaded list, else the one before
function loadedNeighbour(page: BuilderPage) {
	const siblings = (folderPages.data ?? []).filter((row: BuilderPage) => row.project_folder === page.project_folder);
	const index = siblings.findIndex((row: BuilderPage) => row.name === page.name);
	if (index === -1) return;
	return siblings[index + 1] ?? siblings[index - 1];
}

export async function deletePage(page: BuilderPage) {
	const wasOpen = isOpen(page);
	const neighbour = wasOpen ? loadedNeighbour(page) : undefined;
	if (!(await usePageStore().deletePage(page))) return;
	notifyPagesChanged();
	if (!wasOpen) return;
	// a search or the row limit can leave the loaded list without the folder's other pages
	const next = neighbour ?? (page.project_folder ? (await firstPageIn(page.project_folder))[0] : undefined);
	router.push(next ? { name: "builder", params: { pageId: next.name } } : { name: "home" });
}

// protected pages and a read-only editor must not be renamed, moved or deleted from here
function isLocked(page: BuilderPage) {
	return (Boolean(page.is_standard) && !window.is_developer_mode) || (isOpen(page) && useBuilderStore().readOnlyMode);
}

const folderNames = (): string[] =>
	(builderProjectFolder.data ?? []).map((folder: BuilderProjectFolder) => folder.folder_name);

export function pageMenu(page: BuilderPage) {
	const pageStore = usePageStore();
	const moveTargets = [
		{
			label: __("New folder…"),
			icon: "lucide-folder-plus",
			onClick: () => promptNewFolder((folder) => movePage(page, folder)),
		},
		...folderNames().map((name) => ({ label: name, icon: "lucide-folder", onClick: () => movePage(page, name) })),
		{ label: __("No folder"), icon: "lucide-folder-x", onClick: () => movePage(page, "") },
	].filter((target) => target.label !== (page.project_folder || __("No folder")));
	return [
		{
			group: __("Page"),
			hideLabel: true,
			options: [
				{
					label: __("Rename"),
					icon: "lucide-pencil",
					condition: () => !isLocked(page),
					onClick: () => renamePage(page),
				},
				{ label: __("Duplicate"), icon: "lucide-copy", onClick: () => pageStore.duplicatePage(page) },
				{
					label: __("Move to"),
					icon: "lucide-folder-input",
					condition: () => !isLocked(page),
					submenu: moveTargets,
				},
				{
					label: __("View Live Page"),
					icon: "lucide-globe",
					condition: () => Boolean(page.published || page.staging),
					onClick: () => pageStore.openPageInBrowser(page),
				},
				{
					label: __("Unpublish"),
					icon: "lucide-globe-x",
					condition: () => Boolean(page.published || page.staging) && !isLocked(page),
					onClick: () => pageStore.unpublishPage(page),
				},
				{ label: __("View in Desk"), icon: "lucide-arrow-up-right", onClick: () => openInDesk(page) },
			],
		},
		{
			group: __("Danger"),
			hideLabel: true,
			options: [
				{
					label: __("Delete"),
					icon: "lucide-trash",
					theme: "red" as const,
					condition: () => !page.is_standard && !isLocked(page),
					onClick: () => deletePage(page),
				},
			],
		},
	];
}

// onCreate lets a flow like "Move to > New folder" continue with the new folder
export function promptNewFolder(onCreate?: (folder: string) => void) {
	dialog.prompt({
		title: __("New Folder"),
		size: "sm",
		confirmLabel: __("Create"),
		fields: [{ name: "folder_name", label: __("Folder Name"), required: true }],
		onConfirm: async ({ values }) => {
			await builderProjectFolder.insert.submit({ folder_name: values.folder_name });
			onCreate?.(values.folder_name);
		},
	});
}

async function renameFolder(folder: string) {
	dialog.prompt({
		title: __("Rename Folder"),
		size: "sm",
		confirmLabel: __("Rename"),
		fields: [{ name: "name", label: __("Folder Name"), required: true, defaultValue: folder }],
		onConfirm: async ({ values }) => {
			await createResource({ url: "frappe.client.rename_doc" }).submit({
				doctype: "Builder Project Folder",
				old_name: folder,
				new_name: values.name,
			});
			const pageStore = usePageStore();
			// rename_doc rewrites the link on every page, the open page's copy is still the old name
			if (pageStore.activePage?.project_folder === folder) pageStore.activePage.project_folder = values.name;
			await builderProjectFolder.reload();
			// a dashboard showing this folder refetches when its filter changes, a reload here would race it
			const builderStore = useBuilderStore();
			const showingFolder = builderStore.activeFolder === folder;
			if (showingFolder) builderStore.activeFolder = values.name;
			notifyPagesChanged({ reloadDashboard: !showingFolder });
		},
	});
}

async function deleteFolder(folder: string) {
	const confirmed = await confirm(
		__("Delete the folder {0}? Its pages are kept and move to No folder.", [folder]),
	);
	if (!confirmed) return;
	await createResource({ url: "builder.api.delete_folder" }).submit({ folder_name: folder });
	const pageStore = usePageStore();
	if (pageStore.activePage?.project_folder === folder) pageStore.activePage.project_folder = "";
	// a dashboard showing the deleted folder falls back to all pages, where its pages now live
	const { dashboardView, openDashboardView } = useDashboardState();
	if (dashboardView.value === "folder" && useBuilderStore().activeFolder === folder) openDashboardView("all");
	await builderProjectFolder.reload();
	notifyPagesChanged();
	toast.success(__("Folder deleted"));
}

export function folderMenu(folder: BuilderProjectFolder) {
	return [
		{
			group: __("Folder"),
			hideLabel: true,
			options: [
				{
					label: __("Open in Editor"),
					icon: "lucide-square-pen",
					onClick: () => openFolder(folder.folder_name),
				},
				{ label: __("New Page"), icon: "lucide-plus", onClick: () => createPageIn(folder.folder_name) },
				{
					label: __("Rename"),
					icon: "lucide-pencil",
					condition: () => !folder.is_standard,
					onClick: () => renameFolder(folder.folder_name),
				},
			],
		},
		{
			group: __("Danger"),
			hideLabel: true,
			options: [
				{
					label: __("Delete Folder"),
					icon: "lucide-trash",
					theme: "red" as const,
					condition: () => !folder.is_standard,
					onClick: () => deleteFolder(folder.folder_name),
				},
			],
		},
	];
}
