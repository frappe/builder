import type { App } from "vue";
import { frappeRequest } from "frappe-ui";

type TranslationDictionary = Record<string, string>;
type Replacement = string | number;
type TranslationRequest = (options: {
	url: string;
	method: "GET";
	signal: AbortSignal;
}) => Promise<TranslationDictionary>;

const TRANSLATION_REQUEST_TIMEOUT = 5000;

let translations: TranslationDictionary = {};

const requestTranslations: TranslationRequest = (options) =>
	frappeRequest(options) as Promise<TranslationDictionary>;

function format(message: string, replacements: Replacement[]) {
	return message.replace(/\{(\d+)\}/g, (match, index: string) => {
		const replacement = replacements[Number(index)];
		return replacement === undefined ? match : String(replacement);
	});
}

export function setTranslations(dictionary: TranslationDictionary = {}) {
	translations = dictionary;
}

export function __(source: string, replacements: Replacement[] = [], context?: string) {
	const key = context ? `${source}:${context}` : source;
	const translated = translations[key] || translations[source] || source;
	return format(translated, replacements);
}
export async function loadTranslations(
	request: TranslationRequest = requestTranslations,
	timeoutMs = TRANSLATION_REQUEST_TIMEOUT,
) {
	let timeout: ReturnType<typeof setTimeout> | undefined;

	try {
		const controller = new AbortController();
		const dictionary = await Promise.race([
			request({
				url: "builder.api.get_translations",
				method: "GET",
				signal: controller.signal,
			}),
			new Promise<never>((_, reject) => {
				timeout = setTimeout(() => {
					controller.abort();
					reject(new Error("Builder translation request timed out."));
				}, timeoutMs);
			}),
		]);
		setTranslations(dictionary ?? {});
	} catch (error) {
		setTranslations();
		console.warn("Could not load Builder translations. Using English source strings.", error);
	} finally {
		if (timeout !== undefined) clearTimeout(timeout);
	}
}

export default {
	install(app: App) {
		app.config.globalProperties.__ = __;
		window.__ = __;
	},
};
