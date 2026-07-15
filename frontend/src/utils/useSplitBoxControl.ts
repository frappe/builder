import { expandBoxShorthand, normalizeValueWithUnits } from "@/utils/cssUtils";
import { onMounted, ref } from "vue";

type BoxValue = string | number | boolean | null;

interface SplitBoxOptions {
	defaultUnit: string;
	readValue: (state: string | null) => string;
	writeValue: (state: string | null, value: BoxValue) => void;
}

/**
 * Shared state and handlers for box-shorthand controls (margin, padding,
 * border-radius) that toggle between a uniform value and four individual sides.
 */
export function useSplitBoxControl({ defaultUnit, readValue, writeValue }: SplitBoxOptions) {
	const activeState = ref<string | null>(null);
	const linked = ref(true);
	const values = ref<string[]>(expandBoxShorthand(""));

	const sync = (value = readValue(activeState.value)) => {
		values.value = expandBoxShorthand(value);
		linked.value = new Set(values.value).size === 1;
	};

	onMounted(() => sync());

	const applyValue = (value: BoxValue) => {
		writeValue(activeState.value, value);
		values.value = expandBoxShorthand(value);
	};

	const splitValue = (value: unknown) => expandBoxShorthand(value);
	const normalize = (value: BoxValue) => normalizeValueWithUnits(String(value || "0"), defaultUnit);
	const combine = (parts: BoxValue[]) => parts.join(" ");

	const setSplitMode = (split: boolean) => {
		if (split) {
			linked.value = false;
			return;
		}
		applyValue(values.value[0]);
		linked.value = true;
	};

	const setVariantValue = (variant: string, value: BoxValue) => {
		activeState.value = variant;
		applyValue(value);
	};

	return { linked, applyValue, splitValue, normalize, combine, setSplitMode, setVariantValue };
}
