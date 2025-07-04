import styleTokenStore from "@/data/styleTokens";
import { StyleToken } from "@/types/Builder/StyleToken";
import { toKebabCase } from "@/utils/helpers";
import { computed, ComputedRef, ref } from "vue";
import { createStyleTokenVariable, getStyleTokenValue } from "./cssVariables";

interface StyleTokenComposable {
	cssVariables: ComputedRef<Record<string, string>>;
	resolveTokenValue: (value: CSSVariableValue) => string;
	getTokenByName: (name: string) => StyleToken | undefined;
	createTokenVariable: (name: string) => string;
	createToken: (token: Partial<StyleToken>) => Promise<void>;
	updateToken: (token: Partial<StyleToken>) => Promise<void>;
	deleteToken: (name: string) => Promise<void>;
	isLoading: ComputedRef<boolean>;
	tokens: ComputedRef<StyleToken[]>;
}

export const defaultToken: Partial<StyleToken> = {
	token_name: "",
	value: "#000000",
};

let instance: StyleTokenComposable | null = null;

export function useStyleToken(): StyleTokenComposable {
	// Singleton pattern: return existing instance if already created
	if (instance) return instance;

	const isLoading = ref(false);

	const cssVariables = computed(() => {
		return styleTokenStore.data.reduce((obj: Record<string, string>, token: StyleToken) => {
			if (!token.token_name) return obj;
			const cssVariableName = toKebabCase(token.token_name);
			if (token.value) {
				obj[`--${cssVariableName}`] = token.value;
			}
			return obj;
		}, {});
	});

	const resolveTokenValue = (value: CSSVariableValue): string => {
		const token = styleTokenStore.data.find((t: StyleToken) => t.value === value);
		if (token) {
			return getStyleTokenValue(token);
		}
		return value;
	};

	const getTokenByName = (name: string): StyleToken | undefined => {
		return styleTokenStore.data.find((token: StyleToken) => token.token_name === name);
	};

	const createTokenVariable = (name: string): string => {
		const token = getTokenByName(name);
		if (!token) return "";
		return createStyleTokenVariable(token);
	};

	const createToken = async (token: Partial<StyleToken>): Promise<void> => {
		if (!token.token_name || !token.value) {
			throw new Error("Token name and value are required");
		}
		isLoading.value = true;
		try {
			await styleTokenStore.insert.submit({
				...token,
				type: token.type || "Color",
			});
		} finally {
			isLoading.value = false;
		}
	};

	const updateToken = async (token: Partial<StyleToken>): Promise<void> => {
		if (!token.name || !token.token_name || !token.value) {
			throw new Error("Token name, id and value are required");
		}
		isLoading.value = true;
		try {
			await styleTokenStore.setValue.submit(token);
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
			await styleTokenStore.delete.submit(name);
		} finally {
			isLoading.value = false;
		}
	};

	instance = {
		cssVariables,
		resolveTokenValue,
		getTokenByName,
		createTokenVariable,
		createToken,
		updateToken,
		deleteToken,
		isLoading: computed(() => isLoading.value || styleTokenStore.loading),
		tokens: computed(() => styleTokenStore.data || []),
	};

	return instance;
}
