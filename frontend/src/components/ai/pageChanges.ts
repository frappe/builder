/** The rows of Bob's page card: what it proposes for each page and, once answered,
 * how each came out (payload shapes in builder/ai/agent/page_changes.py). */

export type PageResultStatus = "created" | "changed" | "skipped" | "failed";

export interface PageCardRow {
	/** Same as the server's card_key: the page, or "new:/route" for one not created yet. */
	key: string;
	pageId?: string;
	title: string;
	route: string;
	isNew: boolean;
	/** The change lines, or a new page's brief. */
	lines: string[];
	count: number;
	result?: { status: PageResultStatus; detail?: string };
}

interface CardPayload {
	pages?: Array<{ page_id: string; title: string; route: string; changes?: string[]; change_count?: number }>;
	new_pages?: Array<{ title: string; route: string; brief?: string }>;
}

interface PageResult {
	action: "create" | "edit";
	page_id?: string;
	route: string;
	status: PageResultStatus;
	detail?: string;
}

export interface BuildPage {
	page_id: string;
	title: string;
	route: string;
	built?: boolean;
}

const withSlash = (route: string) => "/" + (route || "").replace(/^\//, "");

export function cardRows(meta: { payload?: CardPayload; results?: PageResult[] } = {}): PageCardRow[] {
	const payload = meta.payload || {};
	const rows: PageCardRow[] = [
		...(payload.new_pages || []).map((p) => ({
			key: `new:${withSlash(p.route)}`,
			title: p.title,
			route: withSlash(p.route),
			isNew: true,
			lines: p.brief ? [p.brief] : [],
			count: 0,
		})),
		...(payload.pages || []).map((p) => ({
			key: p.page_id,
			pageId: p.page_id,
			title: p.title,
			route: withSlash(p.route),
			isNew: false,
			lines: p.changes || [],
			count: p.change_count || p.changes?.length || 0,
		})),
	];
	// a created page's result carries the id it got
	for (const result of meta.results || []) {
		const key = result.action === "create" ? `new:${withSlash(result.route)}` : result.page_id;
		const row = rows.find((r) => r.key === key);
		if (!row) continue;
		row.result = { status: result.status, detail: result.detail };
		row.pageId = row.pageId || result.page_id;
	}
	return rows;
}

const count = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** The card asks what it does to which pages, by name when there is one. */
export function cardQuestion(rows: PageCardRow[]): string {
	const created = rows.filter((r) => r.isNew);
	const edited = rows.filter((r) => !r.isNew);
	if (created.length && edited.length)
		return `Create ${count(created.length, "page")} and change ${count(edited.length, "other")}?`;
	if (created.length === 1) return `Create the ${created[0].title} page?`;
	if (created.length) return `Create these ${created.length} pages?`;
	if (edited.length === 1) return `Apply these changes to ${edited[0].title}?`;
	return `Change these ${edited.length} pages?`;
}

/** The apply button names what it does to the pages still ticked. */
export function applyLabel(rows: PageCardRow[]): string {
	const created = rows.filter((r) => r.isNew).length;
	const edited = rows.length - created;
	if (!rows.length) return "Apply";
	if (!edited) return created === 1 ? "Create page" : `Create ${created} pages`;
	if (!created && edited === 1) return "Apply changes";
	return `Apply to ${rows.length} pages`;
}

/** An answered card says how it went in one line. */
export function cardOutcome(rows: PageCardRow[], skippedAll: boolean): string {
	if (skippedAll) return "Skipped, nothing changed";
	const said = (status: PageResultStatus) => rows.filter((r) => r.result?.status === status);
	const named = (list: PageCardRow[]) => (list.length === 1 ? list[0].title : count(list.length, "page"));
	const parts = [
		said("created").length && `created ${named(said("created"))}`,
		said("changed").length && `changed ${named(said("changed"))}`,
		said("failed").length && `${said("failed").length} failed`,
		said("skipped").length && `left out ${said("skipped").length}`,
	].filter(Boolean) as string[];
	const line = parts.join(", ") || "Applied";
	return line.charAt(0).toUpperCase() + line.slice(1);
}

export const RESULT_ICONS: Record<PageResultStatus, string> = {
	created: "lucide-check text-ink-green-6",
	changed: "lucide-check text-ink-green-6",
	skipped: "lucide-minus text-ink-gray-4",
	failed: "lucide-circle-alert text-ink-red-5",
};
