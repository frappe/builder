import blockController from "@/utils/blockController";
import OptionToggle from "../Controls/OptionToggle.vue";
import PropertyControl from "../Controls/PropertyControl.vue";
import ArrayInput from "../ArrayInput.vue";
import ObjectInput from "../ObjectInput.vue";

const componentMap = {
	string: PropertyControl,
	number: PropertyControl,
	boolean: PropertyControl,
	select: PropertyControl,
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
			};
			break;
		case "boolean":
			map = {
				component: OptionToggle,
				enableStates: false,
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
		setModelValue: (val: any) => {
			blockController.setBlockProp(propName, val);
		},
		getModelValue: () => {
			const value = blockController.getFirstSelectedBlock().props?.[propName]?.value;
			return value;
		},
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
		const component = componentMap[propDetails.standardOptions?.type || "string"] || PropertyControl;
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
