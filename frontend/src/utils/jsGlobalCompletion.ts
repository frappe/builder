import { syntaxTree } from "@codemirror/language";

const BOOST_INDEX = 99;

function getAllProperties(obj: Object) {
	const props = new Set();
	let current = obj;

	while (current && current !== Object.prototype) {
		// Get all properties from current level
		Object.getOwnPropertyNames(current).forEach((prop) => {
			props.add(prop);
		});

		// Move up the prototype chain
		current = Object.getPrototypeOf(current);
	}

	return Array.from(props);
}

// Usage
const allDocumentProps = getAllProperties(document);

const completePropertyAfter = ["PropertyName", ".", "?.", "["];
const dontCompleteIn = [
	"TemplateString",
	"LineComment",
	"BlockComment",
	"VariableDefinition",
	"PropertyDefinition",
];

export default function jsCompletionsFromGlobalScope(context: any, blockProps: Record<string, any> = {}) {
	let nodeBefore = syntaxTree(context.state).resolveInner(context.pos, -1);
	const hasProps = Object.keys(blockProps).length > 0;

	if (completePropertyAfter.includes(nodeBefore.name) && nodeBefore.parent?.name == "MemberExpression") {
		let object = nodeBefore.parent.getChild("Expression");
		if (object?.name == "VariableName") {
			let from = /\./.test(nodeBefore.name) ? nodeBefore.to : nodeBefore.from;
			let variableName = context.state.sliceDoc(object.from, object.to);
			if (variableName === "props") {
				// If props is empty, return null immediately (no suggestions)
				if (!hasProps) return null;

				let isBracket = nodeBefore.name === "[";
				return {
					from: context.pos,
					options: Object.keys(blockProps).map((key) => {
						if (isBracket) {
							return {
								label: key,
								displayLabel: `${key}`,
								apply: `"${key}"`,
								type: "property",
							};
						}
						return { label: key, type: "property" };
					}),
				};
			}
			if (typeof window[variableName] == "object") return completeProperties(from, window[variableName]);
		}
	} else if (nodeBefore.name == "VariableName") {
		return completeProperties(nodeBefore.from, window, hasProps ? ["props"] : []);
	} else if (context.explicit && !dontCompleteIn.includes(nodeBefore.name)) {
		return completeProperties(context.pos, window, hasProps ? ["props"] : []);
	}
	return null;
}

function completeProperties(from: any, object: any, extraKeys?: string[]) {
	let options = [];
	for (let name of getAllProperties(object)) {
		options.push({
			label: name,
			type: typeof object[name as string] == "function" ? "function" : "variable",
		});
	}
	if (extraKeys) {
		for (let key of extraKeys) {
			options.push({
				label: key,
				type: "variable",
				boost: BOOST_INDEX,
			});
		}
	}
	return {
		from,
		options,
		validFor: /^[\w$]*$/,
	};
}
