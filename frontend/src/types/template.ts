// Shapes returned by `builder.api.get_template_groups` (the hub catalog).
// Not Frappe doctypes, so they live here rather than in doctypes.ts.

export interface TemplatePageSummary {
	name: string;
	page_title?: string;
	preview?: string;
	// absolute url for remote hub templates; local "My Templates" have none
	live_url?: string;
	template_group?: string;
}

export interface TemplateGroup {
	name: string;
	title: string;
	description?: string;
	preview?: string;
	pages: TemplatePageSummary[];
}
