import builderProjectFolder from "@/data/builderProjectFolder";
import router from "@/router";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { __ } from "@/translation";
import { BuilderPage, BuilderProjectFolder } from "@/types/doctypes";
import { webPages } from "@/data/webPage";
import { createListResource, createResource, dialog } from "frappe-ui";
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

// bumped after any page change so every page list refreshes from the server
export const pagesVersion = ref(0);

function notifyPagesChanged() {
	pagesVersion.value++;
	webPages.reload();
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

async function deletePage(page: BuilderPage) {
	const wasOpen = isOpen(page);
	await usePageStore().deletePage(page);
	const remaining = await createResource({ url: "frappe.client.get_count" }).submit({
		doctype: "Builder Page",
		filters: { name: page.name },
	});
	if (remaining) return;
	notifyPagesChanged();
	if (wasOpen) router.push({ name: "home" });
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
function promptNewFolder(onCreate?: (folder: string) => void) {
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
