<template>
	<div class="flex w-full flex-col gap-2">
		<div @pointerdown="selectActiveState" @focusin="updateActiveState">
			<StylePropertyControl
				propertyKey="borderRadius"
				:component="SplitModeInput"
				label="Radius"
				:unitOptions="['px', '%']"
				:enableStates="true"
				:split="!cornersLinked"
				uniformTitle="Use uniform radius"
				splitTitle="Use individual corner radii"
				:labels="CORNER_LABELS"
				:splitValue="expandRadius"
				:combineValues="combineRadiusValues"
				:normalizeValue="normalizeCornerValue"
				:inputAttrs="{ min: 0 }"
				placeholder="None"
				:getModelValue="() => getBorderRadiusValue(null)"
				:getVariantValue="getBorderRadiusValue"
				:setVariantValue="setVariantValue"
				@update:split="setSplitMode"
				@update:modelValue="setBorderRadius" />
		</div>
	</div>
</template>

<script lang="ts" setup>
import SplitModeInput from "@/components/Controls/SplitModeInput.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { normalizeValueWithUnits } from "@/utils/helpers";
import { onMounted, ref } from "vue";

const CORNER_LABELS = ["TL", "TR", "BR", "BL"];

const activeState = ref<string | null>(null);
const cornersLinked = ref(true);
const cornerValues = ref(["0px", "0px", "0px", "0px"]);

const getStyleKey = (state: string | null = activeState.value) =>
	state ? `${state}:borderRadius` : "borderRadius";

const getBorderRadiusValue = (state: string | null) =>
	(blockController.getStyle(getStyleKey(state)) || "") as string;

const expandRadius = (value: unknown): string[] => {
	const values = String(value ?? "").trim().split(/\s+/).filter(Boolean);
	if (!values.length) return ["0px", "0px", "0px", "0px"];
	if (values.length === 1) return Array(4).fill(values[0]);
	if (values.length === 2) return [values[0], values[1], values[0], values[1]];
	if (values.length === 3) return [values[0], values[1], values[2], values[1]];
	return values.slice(0, 4);
};

const syncCornerValues = (value = getBorderRadiusValue(activeState.value)) => {
	cornerValues.value = expandRadius(value);
	cornersLinked.value = new Set(cornerValues.value).size === 1;
};

onMounted(() => syncCornerValues());

const updateActiveState = (event: FocusEvent) => {
	selectActiveState(event);
};

const selectActiveState = (event: Event) => {
	const variantRow = (event.target as HTMLElement).closest("[data-variant]:not(input)");
	activeState.value = variantRow?.getAttribute("data-variant") || null;
	syncCornerValues();
};

const ensureRoundedContentIsClipped = () => {
	if (!blockController.getStyle("overflowX")) blockController.setStyle("overflowX", "hidden");
	if (!blockController.getStyle("overflowY")) blockController.setStyle("overflowY", "hidden");
};

const setBorderRadius = (value: string | number | boolean | null) => {
	blockController.setStyle(getStyleKey(), value);
	cornerValues.value = expandRadius(String(value || ""));
	if (value) ensureRoundedContentIsClipped();
};

const normalizeCornerValue = (value: string | number | boolean | null) =>
	normalizeValueWithUnits(String(value || "0px"), ["px", "%"], "borderRadius");

const combineRadiusValues = (values: Array<string | number | boolean | null>) => values.join(" ");

const setSplitMode = (split: boolean) => {
	if (split) {
		cornersLinked.value = false;
		return;
	}
	setBorderRadius(cornerValues.value[0]);
	cornersLinked.value = true;
};

const setVariantValue = (variant: string, value: string | number | boolean | null) => {
	activeState.value = variant;
	setBorderRadius(value);
};
</script>
