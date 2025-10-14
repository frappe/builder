import { syntaxTree } from "@codemirror/language";

const completePropertyAfter = ["PropertyName", ".", "?."];
const dontCompleteIn = [
	"TemplateString",
	"LineComment",
	"BlockComment",
	"VariableDefinition",
	"PropertyDefinition",
];

// Create completion source for custom objects
// Currently only two levels of nesting is supported, eg: frappe.session.user
export default function customPythonCompletions(context: any, customCompletions: any) {
	let nodeBefore = syntaxTree(context.state).resolveInner(context.pos, -1);
	if (completePropertyAfter.includes(nodeBefore.name) && nodeBefore.parent?.name == "MemberExpression") {
		let object = nodeBefore.parent.getChild("Expression");

		if (object?.name == "VariableName") {
			let from = /\./.test(nodeBefore.name) ? nodeBefore.to : nodeBefore.from;
			let variableName = context.state.sliceDoc(object.from, object.to);

			if (Object.keys(customCompletions).includes(variableName)) {
				return completeProperties(from, customCompletions[variableName as keyof typeof customCompletions]);
			}
		}
		if (object?.name == "MemberExpression") {
			let from = /\./.test(nodeBefore.name) ? nodeBefore.to : nodeBefore.from;
			let prevName = context.state.sliceDoc(object.from, object.to).split(".")[0];
			let variableName = context.state.sliceDoc(object.from, object.to).split(".")[1];

			if (
				Object.keys(customCompletions).includes(prevName) &&
				variableName in customCompletions[prevName] &&
				typeof customCompletions[prevName][
					variableName as keyof (typeof customCompletions)[typeof prevName]
				] == "object"
			)
				return completeProperties(
					from,
					customCompletions[prevName][variableName as keyof (typeof customCompletions)[typeof prevName]],
				);
		}
	} else if (nodeBefore.name == "VariableName") {
		return {
			from: nodeBefore.from,
			options: [
				{ label: "data", type: "class" },
				...Object.keys(customCompletions).map((item) => {
					return { label: item, type: "class" };
				}),
			],
			validFor: /^[\w$]*$/,
		};
	} else if (context.explicit && !dontCompleteIn.includes(nodeBefore.name)) {
		return {
			from: nodeBefore.from,
			options: [
				{ label: "data", type: "class" },
				...Object.keys(customCompletions).map((item) => {
					return { label: item, type: "class" };
				}),
			],
			validFor: /^[\w$]*$/,
		};
	}
	return null;
}

function completeProperties(from: any, object: any) {
	let options = [];
	for (let name of Object.keys(object)) {
		options.push({
			label: name,
			type: object[name]["type"] ? object[name]["type"] : "variable",
		});
	}
	return {
		from,
		options,
		validFor: /^[\w$]*$/,
	};
}
