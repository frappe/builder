import accessibilitySection from "@/components/BlockPropertySections/AccessibilitySection";
import dimensionSection from "@/components/BlockPropertySections/DimensionSection";
import imageOptionsSection from "@/components/BlockPropertySections/ImageOptionsSection";
import layoutSection from "@/components/BlockPropertySections/LayoutSection";
import positionSection from "@/components/BlockPropertySections/PositionSection";
import spacingSection from "@/components/BlockPropertySections/SpacingSection";
import styleSection from "@/components/BlockPropertySections/StyleSection";
import transitionSection from "@/components/BlockPropertySections/TransitionSection";
import typographySection from "@/components/BlockPropertySections/TypographySection";
import { isValidCSSPropertyName } from "@/utils/cssMetadata";
import { stripStatePrefix, toCSSProperty } from "@/utils/helpers";

type SectionProperty = {
	getProps?: () => Record<string, unknown> | undefined;
	ownedStyleProperties?: string[];
};

type PropertySection = {
	properties: SectionProperty[] | (() => SectionProperty[]);
};

const curatedSections = [
	accessibilitySection,
	dimensionSection,
	imageOptionsSection,
	layoutSection,
	positionSection,
	spacingSection,
	styleSection,
	transitionSection,
	typographySection,
] as PropertySection[];

const getSectionProperties = (section: PropertySection) =>
	typeof section.properties === "function" ? section.properties() : section.properties;

const addSectionProperties = (section: PropertySection, properties: Set<string>) => {
	getSectionProperties(section).forEach((property) => {
		property.ownedStyleProperties?.forEach((styleProperty) => properties.add(styleProperty));
		// descriptors may read block state that is unavailable here; ownedStyleProperties covers those
		let props: Record<string, unknown> | undefined;
		try {
			props = property.getProps?.();
		} catch {
			return;
		}
		const propertyKey = props?.propertyKey || props?.property;
		if (typeof propertyKey === "string") properties.add(toCSSProperty(propertyKey));
	});
};

let curatedProperties: Set<string> | null = null;

// properties owned by a dedicated Builder control, so More Styles must not offer them
const getCuratedStyleProperties = () => {
	if (!curatedProperties) {
		curatedProperties = new Set();
		curatedSections.forEach((section) => addSectionProperties(section, curatedProperties as Set<string>));
	}
	return curatedProperties;
};

const isCuratedStyleProperty = (property: string) => getCuratedStyleProperties().has(property);

// properties on a block that only More Styles can edit
const getNonCuratedProperties = (styleMap: BlockStyleMap) => {
	const properties = new Set<string>();
	Object.keys(styleMap).forEach((style) => {
		const property = stripStatePrefix(toCSSProperty(style));
		if (!isCuratedStyleProperty(property) && isValidCSSPropertyName(property)) properties.add(property);
	});
	return properties;
};

export { getCuratedStyleProperties, getNonCuratedProperties, isCuratedStyleProperty };
