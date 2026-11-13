/** The rows Bob's multi-page messages list: what a confirm card proposes for each
 * page, and how each page came out once applied or built (see
 * builder/ai/agent/page_changes.py for the payload shapes). */

export type PageRowState = "new" | "edit" | "created" | "changed" | "built" | "failed";

export interface PageRow {
	key: string;
	pageId?: string;
	title: string;
	route: string;
	state: PageRowState;
	lines: string[];
}

interface ProposedPages {
	pages?: Array<{ page_id: string; title: string; route: string; changes?: string[] }>;
	new_pages?: Array<{ title: string; route: string; brief?: string }>;
}

interface PageResult {
	page_id?: string;
	title: string;
	route: string;
	status: "created" | "changed" | "built" | "failed";
	detail?: string;
}

const withSlash = (route: string) => "/" + (route || "").replace(/^\//, "");

export function proposedRows(payload: ProposedPages = {}): PageRow[] {
	const created = (payload.new_pages || []).map((p) => ({
		key: `new:${p.route}`,
		title: p.title,
		route: withSlash(p.route),
		state: "new" as const,
		lines: p.brief ? [p.brief] : [],
	}));
	const edited = (payload.pages || []).map((p) => ({
		key: p.page_id,
		pageId: p.page_id,
		title: p.title,
		route: withSlash(p.route),
		state: "edit" as const,
		lines: p.changes || [],
	}));
	return [...created, ...edited];
}

export function resultRows(results: PageResult[] = []): PageRow[] {
	return results.map((r, i) => ({
		key: r.page_id || `${r.route}:${i}`,
		pageId: r.page_id,
		title: r.title,
		route: withSlash(r.route),
		state: r.status,
		// a change list already sat on the card above; only a failure needs saying again
		lines: r.status === "failed" && r.detail ? [r.detail.charAt(0).toUpperCase() + r.detail.slice(1)] : [],
	}));
}

/** The apply button names what it does: creating, changing, or both. */
export function applyPagesLabel(payload: ProposedPages = {}): string {
	const created = payload.new_pages?.length || 0;
	const edited = payload.pages?.length || 0;
	if (created && !edited) return created === 1 ? "Create page" : `Create ${created} pages`;
	if (edited && !created) return edited === 1 ? "Apply changes" : `Apply to ${edited} pages`;
	return "Apply all";
}
