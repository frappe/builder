import PropsEditor from "../PropsEditor.vue";
import blockController from "@/utils/blockController";
import OptionToggle from "../Controls/OptionToggle.vue";
import PropertyControl from "../Controls/PropertyControl.vue";
import ArrayInput from "../ArrayInput.vue";

const componentMap = {
	string: PropertyControl,
	number: PropertyControl,
	boolean: PropertyControl,
	select: PropertyControl,
	array: ArrayInput,
	object: PropsEditor,
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
		...map,
	};
	return map;
};

const getStandardProps = (allProps: BlockProps) => {
	console.log("all props: ", allProps);
	const standardProps: BlockProps = {};
	for (const [propKey, propDetails] of Object.entries(allProps || {})) {
		if (propDetails.isStandard) {
			standardProps[propKey] = propDetails;
		}
	}
	console.log("standard props: ", standardProps);
	return standardProps;
};

const getStandardPropsInputSection = () => {
	const standardProps = getStandardProps(blockController.getBlockProps());
	console;
	const sections = [];
	for (const [propKey, propDetails] of Object.entries(standardProps)) {
		console.log({ propKey, propDetails });
		const component = componentMap[propDetails.standardOptions?.type || "string"] || PropertyControl;
		const getProps = () => {
			const props = getPropsMap(propKey, propDetails);
			console.log("props for standard prop input: ", props);
			return props;
		};
		sections.push({
			component,
			getProps,
			searchKeyWords: propKey,
		});
	}
	console.log("standard props sections: ", sections);
	return sections;
};

export default {
	name: "Standard Props",
	properties: getStandardPropsInputSection,
	collapsed: false,
	condition: () => blockController.getFirstSelectedBlock().isExtendedFromComponent(),
};
