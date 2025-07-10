import builderVariableStore from "@/data/builderVariable";
import { BuilderVariable } from "@/types/Builder/BuilderVariable";
import { toKebabCase } from "@/utils/helpers";
import { computed, ComputedRef, ref } from "vue";

interface builderVariableComposable {
	cssVariables: ComputedRef<Record<string, string>>;
	resolveTokenValue: (value: CSSVariableName) => string;
	getTokenByName: (name: string) => BuilderVariable | undefined;
	createToken: (token: Partial<BuilderVariable>) => Promise<void>;
	updateToken: (token: Partial<BuilderVariable>) => Promise<void>;
	deleteToken: (name: string) => Promise<void>;
	isLoading: ComputedRef<boolean>;
	tokens: ComputedRef<BuilderVariable[]>;
}

export const defaultToken: Partial<BuilderVariable> = {
	token_name: "",
	value: "#000000",
};

let instance: builderVariableComposable | null = null;

export function useBuilderVariable(): builderVariableComposable {
	if (instance) return instance;

	const isLoading = ref(false);

	const cssVariables = computed(() => {
		return builderVariableStore.data.reduce((obj: Record<string, string>, token: BuilderVariable) => {
			if (!token.token_name) return obj;
			const cssVariableName = toKebabCase(token.token_name);
			if (token.value) {
				obj[`--${cssVariableName}`] = token.value;
			}
			return obj;
		}, {});
	});

	const resolveTokenValue = (value: CSSVariableName): string => {
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

	const getTokenByName = (name: string): BuilderVariable | undefined => {
		return builderVariableStore.data.find((token: BuilderVariable) => token.token_name === name);
	};

	const createToken = async (token: Partial<BuilderVariable>): Promise<void> => {
		if (!token.token_name || !token.value) {
			throw new Error("Token name and value are required");
		}
		isLoading.value = true;
		try {
			await builderVariableStore.insert.submit({
				...token,
				type: token.type || "Color",
			});
		} finally {
			isLoading.value = false;
		}
	};

	const updateToken = async (token: Partial<BuilderVariable>): Promise<void> => {
		if (!token.name || !token.token_name || !token.value) {
			throw new Error("Token name, id and value are required");
		}
		isLoading.value = true;
		try {
			await builderVariableStore.setValue.submit(token);
		} finally {
			isLoading.value = false;
		}
	};

	const deleteToken = async (name: string): Promise<void> => {
		if (!name) {
			throw new Error("Token name is required");
		}
		isLoading.value = true;
		try {
			await builderVariableStore.delete.submit(name);
		} finally {
			isLoading.value = false;
		}
	};

	instance = {
		cssVariables,
		resolveTokenValue,
		getTokenByName,
		createToken,
		updateToken,
		deleteToken,
		isLoading: computed(() => isLoading.value || builderVariableStore.loading),
		tokens: computed(() => builderVariableStore.data || []),
	};

	return instance;
}
