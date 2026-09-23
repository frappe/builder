import { pagesWithUnpublishedChanges } from "@/data/webPage";
import { __ } from "@/translation";
import { BuilderPage } from "@/types/doctypes";

export type PageStatus = {
	label: string;
	tooltip: string;
	dotClass: string;
};

const LIVE = "text-ink-green-7";
const STAGING = "text-ink-violet-8";
const DRAFT = "text-ink-gray-4";
// the dot paints itself from the text colour, so both shapes share one palette.
// Hollow reads as "something here isn't live": a draft, or edits waiting to publish.
const FILLED = "bg-current";
const HOLLOW = "border-[1.5px] border-current";

// draft_blocks is cleared on publish, so it is exactly "edited since last publish".
// Dashboard rows don't carry it (it's the whole page), a names-only query stands in.
function hasUnpublishedChanges(page: BuilderPage) {
	if (page.draft_blocks !== undefined) return Boolean(page.draft_blocks);
	return Boolean(pagesWithUnpublishedChanges.getRow(page.name));
}

function liveStatus(label: string, color: string, pending: boolean): PageStatus {
	return {
		label,
		tooltip: pending ? `${label} · ${__("Unpublished changes")}` : label,
		dotClass: `${pending ? HOLLOW : FILLED} ${color}`,
	};
}

export function getPageStatus(page: BuilderPage): PageStatus {
	if (page.published) return liveStatus(__("Live"), LIVE, hasUnpublishedChanges(page));
	if (page.staging) return liveStatus(__("Staging"), STAGING, hasUnpublishedChanges(page));
	return { label: __("Draft"), tooltip: __("Draft"), dotClass: `${HOLLOW} ${DRAFT}` };
}
