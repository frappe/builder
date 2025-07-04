import styleTokenStore from "@/data/styleTokens";
import { StyleToken } from "@/types/Builder/StyleToken";
import { toKebabCase } from "@/utils/helpers";
import { computed, ComputedRef, ref } from "vue";

interface StyleTokenComposable {
	cssVariables: ComputedRef<Record<string, string>>;
	resolveTokenValue: (value: CSSVariableName) => string;
	getTokenByName: (name: string) => StyleToken | undefined;
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

	const getTokenByName = (name: string): StyleToken | undefined => {
		return styleTokenStore.data.find((token: StyleToken) => token.token_name === name);
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
		createToken,
		updateToken,
		deleteToken,
		isLoading: computed(() => isLoading.value || styleTokenStore.loading),
		tokens: computed(() => styleTokenStore.data || []),
	};

	return instance;
}
