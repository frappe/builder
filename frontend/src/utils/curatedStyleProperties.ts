import accessibilitySection from "@/components/BlockPropertySections/AccessibilitySection";
import dimensionSection from "@/components/BlockPropertySections/DimenstionSection";
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

// composite handlers (background, borders, grid, spacing...) do not expose a single
// propertyKey, so the properties they own are listed here instead of being inferred
const compositeProperties = [
	"align-content",
	"align-items",
	"align-self",
	"background",
	"background-attachment",
	"background-blend-mode",
	"background-clip",
	"background-color",
	"background-image",
	"background-origin",
	"background-position",
	"background-repeat",
	"background-size",
	"border",
	"border-bottom-left-radius",
	"border-bottom-right-radius",
	"border-color",
	"border-radius",
	"border-style",
	"border-top-left-radius",
	"border-top-right-radius",
	"border-width",
	"bottom",
	"box-shadow",
	"column-gap",
	"display",
	"flex",
	"flex-basis",
	"flex-direction",
	"flex-flow",
	"flex-grow",
	"flex-shrink",
	"flex-wrap",
	"gap",
	"grid-auto-columns",
	"grid-auto-flow",
	"grid-auto-rows",
	"grid-column",
	"grid-column-end",
	"grid-column-start",
	"grid-row",
	"grid-row-end",
	"grid-row-start",
	"grid-template",
	"grid-template-areas",
	"grid-template-columns",
	"grid-template-rows",
	"height",
	"justify-content",
	"justify-items",
	"justify-self",
	"left",
	"margin",
	"margin-bottom",
	"margin-left",
	"margin-right",
	"margin-top",
	"max-height",
	"max-width",
	"min-height",
	"min-width",
	"object-fit",
	"order",
	"padding",
	"padding-bottom",
	"padding-left",
	"padding-right",
	"padding-top",
	"place-content",
	"place-items",
	"place-self",
	"position",
	"right",
	"rotate",
	"row-gap",
	"top",
	"width",
];

const getSectionProperties = (section: PropertySection) =>
	typeof section.properties === "function" ? section.properties() : section.properties;

const addSectionProperties = (section: PropertySection, properties: Set<string>) => {
	getSectionProperties(section).forEach((property) => {
		// descriptors may read block state that is unavailable here; compositeProperties covers those
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
		curatedProperties = new Set(compositeProperties);
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
