import builderTokenStore from "@/data/builderToken";
import { BuilderToken } from "@/types/doctypes";
import { computed } from "vue";

export const defaultBuilderToken = {
	token_name: "",
	value: "#000000",
	type: "Color" as const,
	dark_value: undefined as string | undefined,
	group: undefined as string | undefined,
};

let instance: ReturnType<typeof builderTokenComposable> | null = null;

function builderTokenComposable() {
	const cssVariables = computed(() => {
		return (builderTokenStore.data || []).reduce(
			(obj: Record<string, string>, builderToken: BuilderToken) => {
				if (!builderToken.name || !builderToken.value) return obj;
				obj[`--${builderToken.name}`] = builderToken.value;
				return obj;
			},
			{},
		);
	});

	const darkCssVariables = computed(() => {
		return (builderTokenStore.data || []).reduce(
			(obj: Record<string, string>, builderToken: BuilderToken) => {
				if (!builderToken.name || !builderToken.dark_value) return obj;
				obj[`--${builderToken.name}`] = builderToken.dark_value;
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
		const variable = (builderTokenStore.data || []).find(
			(builderToken: BuilderToken) => builderToken.name === name,
		);
		return variable?.token_name || null;
	};

	const createVariable = async (builderToken: Partial<BuilderToken>) => {
		if (!builderToken.token_name || !builderToken.value) {
			throw new Error("Variable name and value are required");
		}
		return await builderTokenStore.insert.submit({
			...defaultBuilderToken,
			...builderToken,
		});
	};

	const updateVariable = async (builderToken: Partial<BuilderToken>) => {
		if (!builderToken.name || !builderToken.token_name || !builderToken.value) {
			throw new Error("Variable name, id and value are required");
		}
		return await builderTokenStore.setValue.submit(builderToken);
	};

	const deleteVariable = async (name: string) => {
		if (!name) {
			throw new Error("Variable name is required");
		}
		await builderTokenStore.delete.submit(name);
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
			get: () => (builderTokenStore.data as BuilderToken[]) || [],
			set: (value: BuilderToken[]) => {
				builderTokenStore.data = value;
			},
		}),
	};
}

export function useBuilderToken() {
	if (instance) return instance;
	instance = builderTokenComposable();
	return instance;
}
