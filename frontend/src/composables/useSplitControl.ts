import blockController from "@/utils/blockController";
import { ref, watch } from "vue";

export type SplitValue = string | number | boolean | null;

interface UseSplitControlOptions {
	enableSlider?: boolean;
	splitOptions?: Array<{ label: string; value: boolean; icon: string; tooltip: string }>;
	getMergedValue?: (parts: SplitValue[]) => SplitValue;
}

export function useSplitControl(
	toControlValues: (value: unknown) => SplitValue[],
	readValue: (state: string | null) => string,
	options: UseSplitControlOptions = {},
) {
	const splitModes = ref<Record<string, boolean>>({});

	watch(
		() => blockController.getSelectedBlocks(),
		() => (splitModes.value = {}),
	);

	const getControlAttrs = (variant: string | null) => {
		const key = variant ?? "main";
		const attrs: Record<string, unknown> = {
			split:
				new Set(toControlValues(readValue(variant))).size > 1 ||
				(splitModes.value[key] ?? false),
			enableSlider: options.enableSlider ?? true,
			"onUpdate:split": (split: boolean) => (splitModes.value[key] = split),
		};
		if (options.splitOptions) {
			attrs.splitOptions = options.splitOptions;
		}
		return attrs;
	};

	const getMergedValue =
		options.getMergedValue ?? ((parts: SplitValue[]) => parts[0] ?? "0px");

	return { splitModes, getControlAttrs, getMergedValue };
}
