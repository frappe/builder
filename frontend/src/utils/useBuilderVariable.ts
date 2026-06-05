import builderVariableStore from "@/data/builderVariable";
import { BuilderVariable } from "@/types/doctypes";
import { computed } from "vue";

export const defaultBuilderVariable = {
	variable_name: "",
	value: "#000000",
	type: "Color" as const,
	dark_value: undefined as string | undefined,
	group: undefined as string | undefined,
};

let instance: ReturnType<typeof builderVariableComposable> | null = null;

function builderVariableComposable() {
	const cssVariables = computed(() => {
		return (builderVariableStore.data || []).reduce(
			(obj: Record<string, string>, builderVariable: BuilderVariable) => {
				if (!builderVariable.name || !builderVariable.value) return obj;
				obj[`--${builderVariable.name}`] = builderVariable.value;
				return obj;
			},
			{},
		);
	});

	const darkCssVariables = computed(() => {
		return (builderVariableStore.data || []).reduce(
			(obj: Record<string, string>, builderVariable: BuilderVariable) => {
				if (!builderVariable.name || !builderVariable.dark_value) return obj;
				obj[`--${builderVariable.name}`] = builderVariable.dark_value;
				return obj;
			},
			{},
		);
	});

	// extracts the variable key (e.g. "--uuid") from values like "var(--uuid)" or "--uuid"
	const extractVariableKey = (value: string): string | null => {
		if (!value || value.startsWith("#")) {
			return null;
		}

		let variableName = value;
		if (variableName.startsWith("var(--")) {
			const match = variableName.match(/^var\(\s*(--[^) ,]+)/);
			variableName = match ? match[1] : variableName;
		} else if (!variableName.startsWith("--")) {
			return null;
		}

		return variableName;
	};

	const resolveVariableValue = (value: string, isDarkMode = false): string => {
		const key = extractVariableKey(value);
		if (!key) {
			return value;
		}

		const variables = isDarkMode ? darkCssVariables.value : cssVariables.value;
		return variables[key] ?? cssVariables.value[key] ?? value;
	};

	const getVariableName = (value: string): string | null => {
		const key = extractVariableKey(value);
		if (!key) {
			return null;
		}

		const name = key.slice(2);
		const variable = (builderVariableStore.data || []).find(
			(builderVariable: BuilderVariable) => builderVariable.name === name,
		);
		return variable?.variable_name || null;
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
		return await builderVariableStore.setValue.submit(builderVariable);
	};

	const deleteVariable = async (name: string) => {
		if (!name) {
			throw new Error("Variable name is required");
		}
		await builderVariableStore.delete.submit(name);
	};

	return {
		cssVariables,
		darkCssVariables,
		resolveVariableValue,
		getVariableName,
		createVariable,
		updateVariable,
		deleteVariable,
		variables: computed({
			get: () => (builderVariableStore.data as BuilderVariable[]) || [],
			set: (value: BuilderVariable[]) => {
				builderVariableStore.data = value;
			},
		}),
	};
}

export function useBuilderVariable() {
	if (instance) return instance;
	instance = builderVariableComposable();
	return instance;
}
