import Autocomplete from "@/components/Controls/Autocomplete.vue";
import ColorInput from "@/components/Controls/ColorInput.vue";
import RangeInput from "@/components/Controls/RangeInput.vue";
import cssPropertyMetadata from "@/data/cssPropertyMetadata.json";
import {
	BORDER_UNIT_OPTIONS,
	BOX_UNIT_OPTIONS,
	DIMENSION_UNIT_OPTIONS,
	ROTATION_UNIT_OPTIONS,
} from "@/utils/unitOptions";
import type { Component } from "vue";

// see scripts/generate-css-property-metadata.mjs
type CSSPropertyMetadata = {
	kind: "color" | "length" | "integer" | "number" | "keyword";
	keywords?: string[];
	baseline?: boolean;
};

type Option = { label: string; value: string };

type StyleControlConfig = {
	component?: Component;
	options?: Option[];
	controlAttrs?: Record<string, unknown>;
	enableSlider?: boolean;
	unitOptions?: string[];
	minValue?: number;
	maxValue?: number | null;
	defaultValue?: string | number;
	step?: number;
	min?: number;
	max?: number;
};

const MAX_SEARCH_RESULTS = 50;

const metadata = cssPropertyMetadata as Record<string, CSSPropertyMetadata>;

const baselineCSSProperties = Object.keys(metadata).filter((property) => metadata[property].baseline);

const cssPropertyNamePattern = /^-?[a-z][a-z0-9-]*$/;

const isValidCSSPropertyName = (property: string) => cssPropertyNamePattern.test(property);

const getKeywordOptions = (property: string): Option[] =>
	(metadata[property]?.keywords || []).map((keyword) => ({ label: keyword, value: keyword }));

const keywordControl = (property: string): StyleControlConfig => ({
	component: Autocomplete,
	options: getKeywordOptions(property),
});

// properties whose inferred control is not the one the editor wants
const propertySpecificControls: Record<string, () => StyleControlConfig> = {
	"z-index": () => ({
		component: Autocomplete,
		options: getKeywordOptions("z-index"),
		enableSlider: true,
		minValue: -100,
	}),
	opacity: () => ({
		component: RangeInput,
		enableSlider: false,
		min: 0,
		max: 1,
		step: 0.01,
		defaultValue: 1,
	}),
	rotate: () => ({
		enableSlider: true,
		unitOptions: ROTATION_UNIT_OPTIONS,
		minValue: -360,
		maxValue: 360,
		defaultValue: 0,
	}),
};

const controlsByKind: Record<CSSPropertyMetadata["kind"], (property: string) => StyleControlConfig> = {
	color: () => ({ component: ColorInput, controlAttrs: { popoverOffset: 120 } }),
	length: (property) => ({
		...keywordControl(property),
		enableSlider: true,
		unitOptions: property.includes("border") ? BORDER_UNIT_OPTIONS : DIMENSION_UNIT_OPTIONS,
	}),
	integer: (property) => ({ ...keywordControl(property), enableSlider: true }),
	number: (property) => ({ ...keywordControl(property), enableSlider: true, unitOptions: BOX_UNIT_OPTIONS }),
	keyword: (property) => (metadata[property]?.keywords ? keywordControl(property) : {}),
};

const controlCache = new Map<string, StyleControlConfig>();

const buildControl = (property: string) => {
	const buildSpecificControl = propertySpecificControls[property];
	if (buildSpecificControl) return buildSpecificControl();
	const kind = metadata[property]?.kind;
	return kind ? controlsByKind[kind](property) : {};
};

const getCSSPropertyControl = (property: string) => {
	if (!controlCache.has(property)) {
		controlCache.set(property, buildControl(property));
	}
	return controlCache.get(property) as StyleControlConfig;
};

const normalizeSearchText = (value: string) => value.toLowerCase().replace(/[^a-z0-9]/g, "");

const getFuzzySearchScore = (query: string, property: string) => {
	const normalizedQuery = query.toLowerCase();
	const compactQuery = normalizeSearchText(query);
	const compactProperty = normalizeSearchText(property);

	if (!compactQuery) return 0;
	if (property.includes(normalizedQuery)) return property.indexOf(normalizedQuery);
	if (compactProperty.includes(compactQuery)) return 25 + compactProperty.indexOf(compactQuery);

	let score = 100;
	let previousIndex = -1;

	for (const character of compactQuery) {
		const index = compactProperty.indexOf(character, previousIndex + 1);
		if (index === -1) return null;

		const gap = index - previousIndex - 1;
		score += gap * 2;
		previousIndex = index;
	}

	return score + compactProperty.length - compactQuery.length;
};

const getCSSPropertyOptions = (query: string, excludedProperties = new Set<string>()) => {
	const normalizedQuery = query.trim().toLowerCase();
	const availableProperties = baselineCSSProperties.filter((property) => !excludedProperties.has(property));

	if (!normalizedQuery) {
		return availableProperties
			.slice(0, MAX_SEARCH_RESULTS)
			.map((property) => ({ label: property, value: property }));
	}

	return availableProperties
		.map((property) => ({ property, score: getFuzzySearchScore(normalizedQuery, property) }))
		.filter((result): result is { property: string; score: number } => result.score !== null)
		.sort((a, b) => a.score - b.score || a.property.localeCompare(b.property))
		.slice(0, MAX_SEARCH_RESULTS)
		.map(({ property }) => ({ label: property, value: property }));
};

const getCSSValueOptions = (property: string, query: string) => {
	const normalizedQuery = query.toLowerCase();
	return getKeywordOptions(property)
		.filter((option) => !normalizedQuery || option.label.toLowerCase().includes(normalizedQuery))
		.slice(0, MAX_SEARCH_RESULTS);
};

export type { StyleControlConfig };
export { getCSSPropertyControl, getCSSPropertyOptions, getCSSValueOptions, isValidCSSPropertyName };
