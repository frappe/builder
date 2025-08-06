import builderVariableStore from "@/data/builderVariable";
import { BuilderVariable } from "@/types/Builder/BuilderVariable";
import { toKebabCase } from "@/utils/helpers";
import { computed } from "vue";

export const defaultBuilderVariable = {
	variable_name: "",
	value: "#000000",
	type: "Color" as const,
};

let instance: ReturnType<typeof builderVariableComposable> | null = null;

function builderVariableComposable() {
	const cssVariables = computed(() => {
		return builderVariableStore.data.reduce(
			(obj: Record<string, string>, builderVariable: BuilderVariable) => {
				if (!builderVariable.variable_name) return obj;
				const cssVariableName = toKebabCase(builderVariable.variable_name);
				if (builderVariable.value) {
					obj[`--${cssVariableName}`] = builderVariable.value;
				}
				return obj;
			},
			{},
		);
	});

	const resolveVariableValue = (value: string): string => {
		if (value.startsWith("#")) {
			return value;
		}

		let variableName = value;
		if (variableName.startsWith("var(--")) {
			const match = variableName.match(/^var\(\s*([^) ,]+)/);
			variableName = match ? match[1] : variableName;
		} else if (!variableName.startsWith("--")) {
			variableName = `--${toKebabCase(variableName)}`;
		}

		return cssVariables.value[variableName] ?? value;
	};

	const createVariable = async (builderVariable: Partial<BuilderVariable>) => {
		if (!builderVariable.variable_name || !builderVariable.value) {
			throw new Error("Variable name and value are required");
		}
		return await builderVariableStore.insert.submit({
			...defaultBuilderVariable,
			...builderVariable,
		});
	};

	const updateVariable = async (builderVariable: Partial<BuilderVariable>) => {
		if (!builderVariable.name || !builderVariable.variable_name || !builderVariable.value) {
			throw new Error("Variable name, id and value are required");
		}
		await builderVariableStore.setValue.submit(builderVariable);
	};

	const deleteVariable = async (name: string) => {
		if (!name) {
			throw new Error("Variable name is required");
		}
		await builderVariableStore.delete.submit(name);
	};

	return {
		cssVariables,
		resolveVariableValue,
		createVariable,
		updateVariable,
		deleteVariable,
		variables: computed(() => builderVariableStore.data || []),
	};
}

export function useBuilderVariable() {
	if (instance) return instance;
	instance = builderVariableComposable();
	return instance;
}
