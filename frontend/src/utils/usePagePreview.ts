import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { computed, ref, watch } from "vue";

/** Scripts + same-origin DOM access; modals for alert/confirm; no top navigation or popups. */
export const PREVIEW_IFRAME_SANDBOX = "allow-scripts allow-same-origin allow-modals";

export function buildPagePreviewUrl(
	pageId: string,
	routeVariables: Record<string, string>,
	prefersColorScheme: "light" | "dark",
	refreshKey = 0,
) {
	const queryParams: Record<string, string | number> = {
		page: pageId,
		...routeVariables,
		prefers_color_scheme: prefersColorScheme,
	};
	if (refreshKey) {
		queryParams._refresh = refreshKey;
	}
	return `/api/method/builder.api.get_page_preview_html?${Object.entries(queryParams)
		.map(([key, value]) => `${key}=${encodeURIComponent(String(value))}`)
		.join("&")}`;
}

export function applyPreviewColorScheme(
	iframe: HTMLIFrameElement | null | undefined,
	scheme: "dark" | "light",
) {
	try {
		const doc = iframe?.contentWindow?.document;
		if (doc?.documentElement) {
			doc.documentElement.setAttribute("data-prefers-color-scheme", scheme);
		}
	} catch {
		// ignore cross-origin or timing errors
	}
}

/** Block navigation away from the previewed page; in-document hash links still work. */
export function lockPreviewNavigation(iframe: HTMLIFrameElement | null | undefined) {
	try {
		const doc = iframe?.contentWindow?.document;
		if (!doc || doc.documentElement.dataset.builderPreviewLocked === "true") {
			return;
		}
		doc.documentElement.dataset.builderPreviewLocked = "true";

		doc.addEventListener(
			"click",
			(ev) => {
				const anchor = (ev.target as Element | null)?.closest("a[href]");
				if (!anchor) {
					return;
				}
				const href = anchor.getAttribute("href")?.trim() ?? "";
				if (!href || href.startsWith("#")) {
					return;
				}
				ev.preventDefault();
				ev.stopPropagation();
			},
			true,
		);

		doc.addEventListener(
			"submit",
			(ev) => {
				ev.preventDefault();
				ev.stopPropagation();
			},
			true,
		);
	} catch {
		// ignore cross-origin or timing errors
	}
}

export function setupPreviewIframe(iframe: HTMLIFrameElement | null | undefined, scheme: "dark" | "light") {
	applyPreviewColorScheme(iframe, scheme);
	lockPreviewNavigation(iframe);
}

export function usePagePreview() {
	const builderStore = useBuilderStore();
	const pageStore = usePageStore();
	const refreshKey = ref(0);
	const previewIframes = ref<Record<string, HTMLIFrameElement | null>>({});
	const previewLoading = ref<Record<string, boolean>>({});

	const previewUrl = computed(() => {
		if (!pageStore.selectedPage) {
			return "";
		}
		return buildPagePreviewUrl(
			pageStore.selectedPage,
			pageStore.routeVariables,
			builderStore.canvasDarkMode ? "dark" : "light",
			refreshKey.value,
		);
	});

	const setPreviewLoading = (device: string, loading: boolean) => {
		previewLoading.value = { ...previewLoading.value, [device]: loading };
	};

	const markPreviewLoading = (devices?: string[]) => {
		const targets = devices ?? Object.keys(previewIframes.value);
		for (const device of targets) {
			if (previewIframes.value[device]) {
				setPreviewLoading(device, true);
			}
		}
	};

	const refreshPreview = () => {
		markPreviewLoading();
		refreshKey.value += 1;
	};

	const setPreviewIframe = (device: string, el: HTMLIFrameElement | null) => {
		if (!el) {
			if (previewIframes.value[device]) {
				previewIframes.value[device] = null;
			}
			return;
		}

		const isNewIframe = previewIframes.value[device] !== el;
		previewIframes.value[device] = el;
		if (isNewIframe) {
			setPreviewLoading(device, true);
		}
	};

	const onIframeLoad = (device: string) => {
		setupPreviewIframe(
			previewIframes.value[device],
			builderStore.canvasDarkMode ? "dark" : "light",
		);
		setPreviewLoading(device, false);
	};

	watch(
		() => builderStore.showPagePreview,
		(active) => {
			if (active) {
				refreshPreview();
			} else {
				previewLoading.value = {};
			}
		},
	);

	watch(previewUrl, () => {
		if (builderStore.showPagePreview) {
			markPreviewLoading();
		}
	});

	watch(
		() => pageStore.savingPage,
		(saving, wasSaving) => {
			if (wasSaving && !saving && builderStore.showPagePreview) {
				refreshPreview();
			}
		},
	);

	return {
		previewUrl,
		refreshKey,
		previewLoading,
		refreshPreview,
		setPreviewIframe,
		onIframeLoad,
	};
}
