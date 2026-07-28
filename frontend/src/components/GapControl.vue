<template>
	<div class="flex w-full flex-col gap-2">
		<StylePropertyControl
			propertyKey="gap"
			:component="SplitModeInput"
			label="Gap"
			:unitOptions="BOX_UNIT_OPTIONS"
			:enableStates="true"
			:enableSlider="true"
			:splits="splits"
			:toControlValues="toControlValues"
			:toModelValue="toModelValue"
			:normalizeValue="normalize"
			:inputAttrs="{ min: 0 }"
			:getModelValue="readValue"
			:getPlaceholder="getPlaceholder"
			:getVariantValue="readValue"
			:getMergedValue="getMergedValue"
			:setModelValue="setModelValue"
			:getControlAttrs="getControlAttrs" />
	</div>
</template>

<script lang="ts" setup>
import SplitModeInput from "@/components/Controls/SplitModeInput.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { collapseGapShorthand, expandGapShorthand, normalizeValueWithUnits } from "@/utils/cssUtils";
import { BOX_UNIT_OPTIONS } from "@/utils/unitOptions";
import { computed, ref, watch } from "vue";

type BoxValue = string | number | boolean | null;

const enableSlider = true;
const splitModes = ref<Record<string, boolean>>({});

watch(
	() => blockController.getSelectedBlocks(),
	() => (splitModes.value = {}),
);

const isColumnDirection = computed(() => {
	const dir = blockController.getNativeStyle("flexDirection") || blockController.getCascadingStyle("flexDirection");
	return String(dir || "").startsWith("column");
});

const splits = computed(() =>
	isColumnDirection.value
		? [{ label: "H" }, { label: "V" }]
		: [{ label: "V" }, { label: "H" }],
);

const readValue = (state: string | null = null) => {
	if (state) {
		return String(blockController.getNativeStyle(`${state}:gap`) ?? "");
	}
	const gap = String(blockController.getNativeStyle("gap") ?? "");
	const rowGap = String(blockController.getNativeStyle("rowGap") ?? "");
	const colGap = String(blockController.getNativeStyle("columnGap") ?? "");
	if (gap) return gap;
	if (rowGap || colGap) return collapseGapShorthand([rowGap || "0px", colGap || "0px"]);
	return "";
};

const getPlaceholder = () => String(blockController.getCascadingStyle("gap") ?? "unset");

const toControlValues = (value: unknown) => {
	const [rowGap, colGap] = expandGapShorthand(value);
	return isColumnDirection.value ? [colGap, rowGap] : [rowGap, colGap];
};

const normalize = (value: BoxValue) => normalizeValueWithUnits(String(value || "0"), "px");

const toModelValue = (parts: BoxValue[]) => {
	const [first, second] = parts;
	return isColumnDirection.value
		? collapseGapShorthand([second, first])
		: collapseGapShorthand([first, second]);
};

const getMergedValue = (parts: BoxValue[]) => parts[0] ?? 0;

const splitOptions = [
	{
		label: "Use for all",
		value: false,
		icon: "lucide-square",
		tooltip: "Use for all",
	},
	{
		label: "Set separately",
		value: true,
		icon: "lucide-layout-grid",
		tooltip: "Set separately",
	},
];

const getControlAttrs = (variant: string | null) => {
	const key = variant ?? "main";
	return {
		split: new Set(toControlValues(readValue(variant))).size > 1 || (splitModes.value[key] ?? false),
		enableSlider,
		splitOptions,
		"onUpdate:split": (split: boolean) => (splitModes.value[key] = split),
	};
};

const setModelValue = (val: string | boolean | number) => {
	if (typeof val === "boolean") return;
	const value = String(val);
	blockController.setStyle("rowGap", null);
	blockController.setStyle("columnGap", null);
	blockController.setStyle("gap", value || null);
};
</script>
