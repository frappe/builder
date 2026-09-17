import { preloadSettingsPanes } from "@/components/Settings";
import { useDashboardState } from "@/composables/useDashboardState";
import { builderSettings } from "@/data/builderSettings";
import { templateGroups } from "@/data/webPage";
import type { TemplateGroup } from "@/types/template";

// kept referenced so the browser holds them in memory; the picker's cards then paint on open
const warmedThumbnails = new Map<string, HTMLImageElement>();
// the catalog has ~100 thumbnails; the cap only bites if it changes during a long session
const MAX_WARMED_THUMBNAILS = 150;

export function prefetchBuilderSettings() {
	whenIdle(() => {
		import("@/components/BuilderSettings.vue");
		preloadSettingsPanes();
		if (!builderSettings.doc) builderSettings.reload();
	});
}

// fetch the template catalog and warm the thumbnails the picker opens on
export function prefetchTemplateGallery() {
	whenIdle(async () => {
		if (!templateGroups.fetched && !templateGroups.loading) {
			try {
				await templateGroups.fetch();
			} catch {
				// background warm-up; a failed fetch keeps the cached catalog, so warm that
			}
		}
		const groups: TemplateGroup[] = templateGroups.data || [];
		prefetchThumbnails(groups);
		// reopening the picker lands on the last group viewed
		const { lastTemplateGroup } = useDashboardState();
		const lastGroup = groups.find((group) => group.name === lastTemplateGroup.value);
		if (lastGroup) prefetchThumbnails(lastGroup.pages);
	});
}

// full-size previews are skipped: too heavy to download and decode ahead of time
export function prefetchThumbnails(items: { thumbnail?: string }[]) {
	for (const { thumbnail } of items) {
		if (!thumbnail || warmedThumbnails.has(thumbnail)) continue;
		const image = new Image();
		image.fetchPriority = "low";
		image.src = thumbnail;
		image.decode().catch(() => warmedThumbnails.delete(thumbnail));
		warmedThumbnails.set(thumbnail, image);
		if (warmedThumbnails.size > MAX_WARMED_THUMBNAILS) {
			// a Map iterates in insertion order, so the first key is the oldest
			const [oldest] = warmedThumbnails.keys();
			warmedThumbnails.delete(oldest);
		}
	}
}

function whenIdle(callback: () => void) {
	if (window.requestIdleCallback) {
		window.requestIdleCallback(callback);
	} else {
		setTimeout(callback, 1000);
	}
}
