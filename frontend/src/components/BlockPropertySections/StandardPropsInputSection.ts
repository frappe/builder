import blockController from "@/utils/blockController";
import OptionToggle from "../Controls/OptionToggle.vue";
import GenericControl from "../Controls/GenericControl.vue";
import ArrayInput from "../ArrayInput.vue";
import ObjectInput from "../ObjectInput.vue";
import ImageUploadInput from "../ImageUploadInput.vue";
import ColorInput from "../Controls/ColorInput.vue";

const componentMap = {
	array: ArrayInput,
	object: ObjectInput,
};

const getPropsMap = (propName: string, propDetails: BlockProps[string]) => {
	const type = propDetails.standardOptions?.type || "string";
	let map = {};
	switch (type) {
		case "string":
		case "number":
			map = {
				enableStates: false,
				allowDynamicValue: true,
			};
			break;
		case "boolean":
			map = {
				component: OptionToggle,
				enableStates: false,
				allowDynamicValue: true,
				options: [
					{ label: propDetails.standardOptions?.options?.trueLabel || "True", value: true },
					{ label: propDetails.standardOptions?.options?.falseLabel || "False", value: false },
				],
			};
			break;
		case "select":
			map = {
				type: "select",
				enableStates: false,
				options:
					propDetails.standardOptions?.options?.options?.map((item: any) => ({
						label: item,
						value: item,
					})) || [],
			};
			break;
		case "image":
			map = {
				component: ImageUploadInput,
				enableStates: false,
				allowDynamicValue: true,
				imageURL: blockController.getBlockProps()[propName].value as string,
				imageFit:
					propDetails.standardOptions?.options?.imageFit ||
					(propDetails.standardOptions?.options?.defaultImageFit as StyleValue),
			};
			break;
		case "color":
			map = {
				component: ColorInput,
			};
			break;
	}
	map = {
		label: propDetails.label || propName,
		dynamicValueFilterOptions: {
			excludeOwnProps: true,
			excludeOwnBlockData: true,
		},
		getDynamicValue: () => {
			if (propDetails.isDynamic) {
				return {
					key: propDetails.value,
					comesFrom: propDetails.comesFrom,
				};
			}
		},
		setDynamicValue: (key: string | null, comesFrom: BlockProps[string]["comesFrom"]) => {
			blockController.setBlockProp(propName, { value: key || "", isDynamic: key !== null, comesFrom });
		},
		setModelValue: (value: any) => {
			blockController.setBlockProp(propName, { value });
		},
		getModelValue: () => {
			const value = blockController.getFirstSelectedBlock().props?.[propName]?.value;
			return value;
		},
		getPlaceholder: () => {
			return propDetails.standardOptions?.options?.defaultValue || null;
		},
		defaultValue:
			type == "boolean"
				? propDetails.standardOptions?.options?.defaultValue == "true"
				: propDetails.standardOptions?.options?.defaultValue,
		...map,
	};
	return map;
};

const getEventsMap = (propName: string, propDetails: BlockProps[string]) => {
	let events: Record<string, Function> = {};
	const type = propDetails.standardOptions?.type || "string";
	switch (type) {
		case "image":
			events = {
				"update:imageURL": (val: string) => blockController.setBlockProp(propName, { value: val }),
				"update:imageFit": (val: StyleValue) =>
					blockController.setBlockProp(propName, {
						standardOptions: { options: { ...propDetails.standardOptions?.options, imageFit: val } },
					}),
			};
			break;
	}
	return events;
};

const getStandardProps = (allProps: BlockProps) => {
	const standardProps: BlockProps = {};
	for (const [propKey, propDetails] of Object.entries(allProps || {})) {
		if (propDetails.isStandard) {
			standardProps[propKey] = propDetails;
		}
	}
	return standardProps;
};

const getStandardPropsInputSection = () => {
	const standardProps = getStandardProps(blockController.getBlockProps());
	const sections = [];
	for (const [propKey, propDetails] of Object.entries(standardProps)) {
		const propType = propDetails.standardOptions?.type;
		const component =
			(propType === "array" || propType === "object" ? componentMap[propType] : undefined) || GenericControl;
		const getProps = () => {
			const props = getPropsMap(propKey, propDetails);
			return props;
		};
		const events = getEventsMap(propKey, propDetails);
		sections.push({
			component,
			getProps,
			events,
			searchKeyWords: [propKey, propDetails.label].join(", "),
		});
	}
	return sections;
};

export default {
	name: "Component Options",
	properties: getStandardPropsInputSection,
	collapsed: false,
	condition: () =>
		Boolean(blockController.getFirstSelectedBlock().extendedFromComponent) &&
		Object.keys(getStandardProps(blockController.getBlockProps())).length > 0,
};
