import {
	propertySections,
	type BlockProperty,
	type PropertySection,
} from "@/components/BlockPropertySections";
import { isValidCSSPropertyName } from "@/utils/cssMetadata";
import { stripStatePrefix, toCSSProperty } from "@/utils/helpers";

const getSectionProperties = (section: PropertySection) =>
	typeof section.properties === "function" ? section.properties() : section.properties;

// descriptors may read block state that is unavailable here; usedStyleProperties covers those
const getControlProperty = (property: BlockProperty) => {
	let props: Record<string, unknown> | undefined;
	try {
		props = property.getProps?.();
	} catch {
		return null;
	}
	const propertyKey = props?.propertyKey || props?.property;
	return typeof propertyKey === "string" ? toCSSProperty(propertyKey) : null;
};

// a used style property maps to its control's property, e.g. margin-top to margin.
// the control's own property must be a used style, so image styles do not map to "src"
const addSectionProperties = (section: PropertySection, controlProperties: Map<string, string>) => {
	getSectionProperties(section).forEach((property) => {
		const controlProperty = getControlProperty(property);
		const usedStyleProperties = property.usedStyleProperties || [];
		const styleControlProperty =
			controlProperty && usedStyleProperties.includes(controlProperty) ? controlProperty : null;
		usedStyleProperties.forEach((styleProperty) =>
			controlProperties.set(styleProperty, styleControlProperty || styleProperty),
		);
		if (controlProperty) controlProperties.set(controlProperty, controlProperty);
	});
};

let cachedControlProperties: Map<string, string> | null = null;

// properties owned by a dedicated Builder control, so More Styles must not offer them
const getControlProperties = () => {
	if (!cachedControlProperties) {
		cachedControlProperties = new Map();
		// all, not visible: a section's condition reads block state, unavailable here
		propertySections.all.value.forEach((section) =>
			addSectionProperties(section, cachedControlProperties as Map<string, string>),
		);
	}
	return cachedControlProperties;
};

const getStylePropertiesWithControls = () => new Set(getControlProperties().keys());

const isStylePropertyWithControls = (property: string) => getControlProperties().has(property);

// the property key of the control that edits this property
const getControlStyleProperty = (property: string) => getControlProperties().get(property);

// properties on a block that only More Styles can edit
const getStylePropertiesWithoutControls = (styleMap: BlockStyleMap) => {
	const properties = new Set<string>();
	Object.keys(styleMap).forEach((style) => {
		const property = stripStatePrefix(toCSSProperty(style));
		if (!isStylePropertyWithControls(property) && isValidCSSPropertyName(property)) properties.add(property);
	});
	return properties;
};

export {
	getControlStyleProperty,
	getStylePropertiesWithControls,
	getStylePropertiesWithoutControls,
	isStylePropertyWithControls,
};
