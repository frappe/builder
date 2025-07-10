import builderVariableStore from "@/data/builderVariable";
import { BuilderVariable } from "@/types/Builder/BuilderVariable";
import { toKebabCase } from "@/utils/helpers";
import { computed, ComputedRef } from "vue";

interface builderVariableComposable {
	cssVariables: ComputedRef<Record<string, string>>;
	resolveVariableValue: (value: CSSVariableName) => string;
	createVariable: (builderVariable: Partial<BuilderVariable>) => Promise<void>;
	updateVariable: (builderVariable: Partial<BuilderVariable>) => Promise<void>;
	deleteVariable: (name: string) => Promise<void>;
	variables: ComputedRef<BuilderVariable[]>;
}

export const defaultBuilderVariable: Partial<BuilderVariable> = {
	variable_name: "",
	value: "#000000",
};

let instance: builderVariableComposable | null = null;

export function useBuilderVariable(): builderVariableComposable {
	if (instance) return instance;
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

	const resolveVariableValue = (value: CSSVariableName): string => {
		if (typeof value === "string" && value.startsWith("#")) {
			return value;
		}
		let variableName = value;
		if (typeof variableName === "string") {
			if (variableName.startsWith("var(--")) {
				const match = variableName.match(/^var\(\s*([^) ,]+)[^)]*\)/);
				if (match) {
					variableName = match[1];
				}
			} else if (variableName.startsWith("--")) {
				// keep as is
			} else {
				variableName = `--${toKebabCase(variableName)}`;
			}
		}
		return cssVariables.value[variableName] ?? value;
	};

	const createVariable = async (builderVariable: Partial<BuilderVariable>): Promise<void> => {
		if (!builderVariable.variable_name || !builderVariable.value) {
			throw new Error("Token name and value are required");
		}
		await builderVariableStore.insert.submit({
			...builderVariable,
			type: builderVariable.type || "Color",
		});
	};

	const updateVariable = async (builderVariable: Partial<BuilderVariable>): Promise<void> => {
		if (!builderVariable.name || !builderVariable.variable_name || !builderVariable.value) {
			throw new Error("Token name, id and value are required");
		}
		await builderVariableStore.setValue.submit(builderVariable);
	};

	const deleteVariable = async (name: string): Promise<void> => {
		if (!name) {
			throw new Error("Token name is required");
		}
		await builderVariableStore.delete.submit(name);
	};

	instance = {
		cssVariables,
		resolveVariableValue,
		createVariable,
		updateVariable,
		deleteVariable,
		variables: computed(() => builderVariableStore.data || []),
	};

	return instance;
}
