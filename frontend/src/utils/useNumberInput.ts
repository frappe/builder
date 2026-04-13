import { computed } from "vue";
import { extractNumberAndUnit } from "@/utils/helpers";

interface UseNumberInputOptions {
	getValue: () => string | number | boolean | null | undefined;
	setValue: (value: string) => void;
	getAttrs?: () => Record<string, unknown>;
}

export function useNumberInput({ getValue, setValue, getAttrs }: UseNumberInputOptions) {
	const hasNumber = computed(() => {
		const value = String(getValue() ?? "").trim();
		return /^-?\d/.test(value);
	});

	const incrementValue = () => {
		const { number, unit } = extractNumberAndUnit(String(getValue() || ""));
		const attrs = getAttrs?.() ?? {};
		const step = attrs.step ? parseFloat(String(attrs.step)) : 1;
		const max = attrs.max !== undefined ? parseFloat(String(attrs.max)) : Infinity;
		const currentNum = parseFloat(number) || 0;
		const newNum = Math.min(max, parseFloat((currentNum + step).toFixed(10)));
		setValue(newNum + unit);
	};

	const decrementValue = () => {
		const { number, unit } = extractNumberAndUnit(String(getValue() || ""));
		const attrs = getAttrs?.() ?? {};
		const step = attrs.step ? parseFloat(String(attrs.step)) : 1;
		const min = attrs.min !== undefined ? parseFloat(String(attrs.min)) : -Infinity;
		const currentNum = parseFloat(number) || 0;
		const newNum = Math.max(min, parseFloat((currentNum - step).toFixed(10)));
		setValue(newNum + unit);
	};

	return { hasNumber, incrementValue, decrementValue };
}