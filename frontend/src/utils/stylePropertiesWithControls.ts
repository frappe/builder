import { propertySections, type PropertySection } from "@/components/BlockPropertySections";
import { isValidCSSPropertyName } from "@/utils/cssMetadata";
import { stripStatePrefix, toCSSProperty } from "@/utils/helpers";

const getSectionProperties = (section: PropertySection) =>
	typeof section.properties === "function" ? section.properties() : section.properties;

const addSectionProperties = (section: PropertySection, properties: Set<string>) => {
	getSectionProperties(section).forEach((property) => {
		property.usedStyleProperties?.forEach((styleProperty) => properties.add(styleProperty));
		// descriptors may read block state that is unavailable here; usedStyleProperties covers those
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

let cachedStyleProperties: Set<string> | null = null;

// properties owned by a dedicated Builder control, so More Styles must not offer them
const getStylePropertiesWithControls = () => {
	if (!cachedStyleProperties) {
		cachedStyleProperties = new Set();
		// all, not visible: a section's condition reads block state, unavailable here
		propertySections.all.value.forEach((section) =>
			addSectionProperties(section, cachedStyleProperties as Set<string>),
		);
	}
	return cachedStyleProperties;
};

const isStylePropertyWithControls = (property: string) => getStylePropertiesWithControls().has(property);

// properties on a block that only More Styles can edit
const getStylePropertiesWithoutControls = (styleMap: BlockStyleMap) => {
	const properties = new Set<string>();
	Object.keys(styleMap).forEach((style) => {
		const property = stripStatePrefix(toCSSProperty(style));
		if (!isStylePropertyWithControls(property) && isValidCSSPropertyName(property)) properties.add(property);
	});
	return properties;
};

export { getStylePropertiesWithControls, getStylePropertiesWithoutControls, isStylePropertyWithControls };
