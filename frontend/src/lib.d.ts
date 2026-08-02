declare module "webfontloader";

type TranslationFunction = (
	source: string,
	replacements?: Array<string | number>,
	context?: string,
) => string;

declare global {
	interface Window {
		__: TranslationFunction;
	}
}

declare module "@vue/runtime-core" {
	interface ComponentCustomProperties {
		__: TranslationFunction;
	}
}

export {};
