import blockController from "@/utils/blockController";
import OptionToggle from "../Controls/OptionToggle.vue";
import GenericControl from "../Controls/GenericControl.vue";
import ArrayInput from "../ArrayInput.vue";
import ObjectInput from "../ObjectInput.vue";

const componentMap = {
	string: GenericControl,
	number: GenericControl,
	boolean: GenericControl,
	select: GenericControl,
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
	}
	map = {
		label: propName,
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
		const component = componentMap[propDetails.standardOptions?.type || "string"] || GenericControl;
		const getProps = () => {
			const props = getPropsMap(propKey, propDetails);
			return props;
		};
		sections.push({
			component,
			getProps,
			searchKeyWords: propKey,
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
