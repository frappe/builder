import builderTokenStore from "@/data/builderToken";
import { BuilderToken } from "@/types/doctypes";
import { toast } from "frappe-ui";
import { computed, ref } from "vue";

export const defaultBuilderToken = {
	token_name: "",
	value: "#000000",
	type: "Color" as const,
	dark_value: undefined as string | undefined,
	group: undefined as string | undefined,
};

// legacy rows can carry a blank or lower-cased type; everything reads it through here
export const tokenType = (token: Partial<BuilderToken>): NonNullable<BuilderToken["type"]> => {
	const type = (token.type || "Color").toLowerCase();
	if (type === "font") return "Font";
	if (type === "dimension") return "Dimension";
	return "Color";
};

type TokenFields = Pick<BuilderToken, "token_name" | "value" | "dark_value" | "group">;
type TokenChange = { name: string; before: TokenFields; after: TokenFields };
type TokenHistoryEntry = { changes: TokenChange[]; at: number };

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
		forgetTokenHistory([name]);
	};

	const fontTokens = computed(() =>
		(builderTokenStore.data || []).filter((t: BuilderToken) => tokenType(t) === "Font" && t.value),
	);

	const tokenUndoStack: TokenHistoryEntry[] = [];
	const tokenRedoStack: TokenHistoryEntry[] = [];
	const tokenHistoryVersion = ref(0);
	const tokenEditVersion = ref(0);
	const pendingEditFlushes = new Set<() => void>();
	const flushPendingEdits = () => pendingEditFlushes.forEach((flush) => flush());

	const clearTokenRedo = () => {
		tokenRedoStack.length = 0;
	};

	const clearTokenHistory = () => {
		tokenUndoStack.length = 0;
		clearTokenRedo();
	};

	const forgetTokenHistory = (names: string[]) => {
		const forgotten = new Set(names);
		for (const stack of [tokenUndoStack, tokenRedoStack]) {
			const kept = stack
				.map((entry) => ({
					...entry,
					changes: entry.changes.filter((change) => !forgotten.has(change.name)),
				}))
				.filter((entry) => entry.changes.length);
			stack.splice(0, stack.length, ...kept);
		}
	};

	const recordTokenChange = (changes: TokenChange[]) => {
		const changed = changes.filter(({ before, after }) =>
			(Object.keys(after) as (keyof TokenFields)[]).some((key) => before[key] !== after[key]),
		);
		if (!changed.length) return;
		tokenUndoStack.unshift({ changes: changed, at: Date.now() });
		clearTokenRedo();
		tokenEditVersion.value++;
	};

	const moveTokenChange = (from: TokenHistoryEntry[], to: TokenHistoryEntry[], side: "before" | "after") => {
		const entry = from.shift();
		if (!entry) return;
		to.unshift({ ...entry, at: Date.now() });
		const values = new Map(entry.changes.map((change) => [change.name, change[side]]));
		builderTokenStore.data = (builderTokenStore.data || []).map((token: BuilderToken) =>
			values.has(token.name) ? { ...token, ...values.get(token.name) } : token,
		);
		tokenHistoryVersion.value++;
		for (const [name, fields] of values) {
			updateVariable({ name, ...fields }).catch((error) =>
				toast.error((error as Error).message || "Failed to update variable"),
			);
		}
	};

	return {
		cssVariables,
		darkCssVariables,
		fontTokens,
		resolveVariableValue,
		getVariableName,
		createVariable,
		updateVariable,
		deleteVariable,
		recordTokenChange,
		clearTokenRedo,
		clearTokenHistory,
		forgetTokenHistory,
		pendingEditFlushes,
		flushPendingEdits,
		undoTokenChange: () => moveTokenChange(tokenUndoStack, tokenRedoStack, "before"),
		redoTokenChange: () => moveTokenChange(tokenRedoStack, tokenUndoStack, "after"),
		lastTokenUndoAt: () => tokenUndoStack[0]?.at ?? 0,
		lastTokenRedoAt: () => tokenRedoStack[0]?.at ?? 0,
		tokenHistoryVersion,
		tokenEditVersion,
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
