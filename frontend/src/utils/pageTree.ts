import builderProjectFolder from "@/data/builderProjectFolder";
import router from "@/router";
import usePageStore from "@/stores/pageStore";
import { __ } from "@/translation";
import { BuilderPage, BuilderProjectFolder } from "@/types/doctypes";
import { webPages } from "@/data/webPage";
import { createListResource, createResource, dialog } from "frappe-ui";

export const sitePages = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: [
		"name",
		"page_name",
		"page_title",
		"route",
		"project_folder",
		"published",
		"staging",
		"is_standard",
	],
	filters: { is_template: 0 },
	// creation order keeps a template's pages in the order the template lists them
	orderBy: "creation asc",
	pageLength: 9999,
	cache: "site-pages",
	auto: true,
});

const isOpen = (page: BuilderPage) => page.name === usePageStore().activePage?.name;

export function openPage(page: BuilderPage) {
	if (!isOpen(page)) router.push({ name: "builder", params: { pageId: page.name } });
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
	// the dashboard lists pages through its own resource, so both refresh
	sitePages.reload();
	webPages.reload();
}

export const movePage = (page: BuilderPage, folder: string) => {
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
	await sitePages.reload();
	if (wasOpen && !sitePages.data?.some((row: BuilderPage) => row.name === page.name)) {
		router.push({ name: "home" });
	}
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
				{ label: __("Rename"), icon: "lucide-pencil", onClick: () => renamePage(page) },
				{ label: __("Duplicate"), icon: "lucide-copy", onClick: () => pageStore.duplicatePage(page) },
				{ label: __("Move to"), icon: "lucide-folder-input", submenu: moveTargets },
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
					condition: () => !page.is_standard,
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
