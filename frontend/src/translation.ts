import type { App } from "vue";

type Replacement = string | number;

export function __(source: string, replacements: Replacement[] = [], context?: string) {
	const messages = window.translated_messages || {};
	const translated = (context && messages[`${source}:${context}`]) || messages[source] || source;
	return translated.replace(/\{(\d+)\}/g, (match, index) => String(replacements[index] ?? match));
}

// the vite dev server serves index.html without the boot payload; fetched
// before mount so module-scope __() calls in route chunks see the catalog
export async function ensureTranslations() {
	if (window.translated_messages) return;
	try {
		const response = await fetch("/api/method/frappe.translate.get_boot_translations");
		window.translated_messages = (await response.json()).message || {};
	} catch {
		window.translated_messages = {};
	}
}

export default {
	install(app: App) {
		app.config.globalProperties.__ = __;
		window.__ = __;
	},
};

declare global {
	interface Window {
		__: typeof __;
		translated_messages?: Record<string, string>;
	}
}

declare module "@vue/runtime-core" {
	interface ComponentCustomProperties {
		__: typeof __;
	}
}
