import { builderSettings } from "@/data/builderSettings";

export function prefetchBuilderSettings() {
	const preloadSettings = () => {
		import("@/components/BuilderSettings.vue");
		if (!builderSettings.doc) builderSettings.reload();
	};
	if (window.requestIdleCallback) {
		window.requestIdleCallback(preloadSettings);
	} else {
		setTimeout(preloadSettings, 1000);
	}
}
