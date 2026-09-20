import { createListResource, createResource } from "frappe-ui";

const webPages = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: [
		"name",
		"route",
		"page_name",
		"preview",
		"page_title",
		"meta_image",
		"creation",
		"published",
		"staging",
		"dynamic_route",
		"modified_by",
		"modified",
		"is_template",
		"authenticated_access",
		"project_folder",
		"is_standard",
		"owner",
	],
	filters: {
		is_template: 0,
	},
	cache: "pages",
	pageLength: 50,
});

// names of live/staged pages carrying edits that aren't published yet, kept out of
// the main list so the heavy draft_blocks column never has to be fetched
const pagesWithUnpublishedChanges = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: ["name"],
	filters: {
		is_template: 0,
		draft_blocks: ["is", "set"],
	},
	orFilters: {
		published: 1,
		staging: 1,
	},
	cache: "pages-with-unpublished-changes",
	// a truncated lookup would quietly show a pending page as fully published, so this
	// matches the ceiling the route tree already fetches pages at
	pageLength: 9999,
});

const templateGroups = createResource({
	url: "builder.api.get_template_groups",
	cache: "template-groups",
});

const searchablePages = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: ["name", "route", "page_name", "page_title"],
	filters: {
		is_template: 0,
	},
	cache: "searchable-pages",
	orderBy: "modified desc",
	pageLength: 10,
});

export { pagesWithUnpublishedChanges, searchablePages, templateGroups, webPages };
