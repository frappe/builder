import { syntaxTree } from "@codemirror/language";

const completePropertyAfter = ["PropertyName", ".", "?.", "[", "("];
const dontCompleteIn = [
	"TemplateString",
	"LineComment",
	"BlockComment",
	"VariableDefinition",
	"PropertyDefinition",
];

const BOOST_INDEX = 99;

// Create completion source for custom objects
// Currently only two levels of nesting is supported, eg: frappe.session.user
export default function customPythonCompletions(
	context: any,
	customCompletions: any,
	mode: "block" | "page" = "page",
	blockProps: Record<string, any> = {},
) {
	let nodeBefore = syntaxTree(context.state).resolveInner(context.pos, -1);
	const hasProps = Object.keys(blockProps).length > 0;
	const propCompletions = {
		from: context.pos,
		options: Object.keys(blockProps).map((key) => {
			return {
				label: key,
				displayLabel: `${key}`,
				apply: `"${key}"`,
				type: "property",
			};
		}),
	};

	if (nodeBefore.name === "(" && nodeBefore.parent?.name === "ArgList") {
		let callExpression = nodeBefore.parent.parent;
		if (callExpression?.name === "CallExpression") {
			let memberExpr = callExpression.getChild("MemberExpression");
			if (memberExpr) {
				let object = memberExpr.getChild("Expression");
				let property = memberExpr.getChild("PropertyName");

				if (object?.name === "VariableName" && property) {
					let objectName = context.state.sliceDoc(object.from, object.to);
					let propertyName = context.state.sliceDoc(property.from, property.to);

					if (objectName === "props" && propertyName === "get" && hasProps) {
						return propCompletions;
					}
				}
			}
		}
	}
	if (completePropertyAfter.includes(nodeBefore.name) && nodeBefore.parent?.name == "MemberExpression") {
		let object = nodeBefore.parent.getChild("Expression");

		if (object?.name == "VariableName") {
			let from = /\./.test(nodeBefore.name) ? nodeBefore.to : nodeBefore.from;
			let variableName = context.state.sliceDoc(object.from, object.to);
			if (variableName === "props") {
				let isBracket = nodeBefore.name === "[";
				if (!hasProps || !isBracket) return null;
				console.log(variableName, blockProps, isBracket);
				return propCompletions;
			}

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
				...(mode == "block"
					? [
							{ label: "block", type: "class", boost: BOOST_INDEX },
							{ label: "props", type: "class", boost: BOOST_INDEX },
					  ]
					: [
							{ label: "data", type: "class", boost: BOOST_INDEX },
							{ label: "page", type: "class", boost: BOOST_INDEX },
					  ]),
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
				...(mode == "block"
					? [
							{ label: "block", type: "class", boost: BOOST_INDEX },
							{ label: "props", type: "class", boost: BOOST_INDEX },
					  ]
					: [
							{ label: "data", type: "class", boost: BOOST_INDEX },
							{ label: "page", type: "class", boost: BOOST_INDEX },
					  ]),
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
