<template>
	<div class="flex w-full flex-col gap-2">
		<div @pointerdown="selectActiveState" @focusin="selectActiveState">
			<StylePropertyControl
				:propertyKey="type"
				:component="SplitModeInput"
				:label="label"
				:unitOptions="UNITS"
				:enableStates="true"
				:enableSlider="true"
				:split="!sidesLinked"
				:uniformTitle="`Use uniform ${type}`"
				:splitTitle="`Use individual ${type} sides`"
				:labels="SIDE_LABELS"
				:splitValue="expandSpacing"
				:combineValues="combineSpacingValues"
				:normalizeValue="normalizeSideValue"
				:inputAttrs="{ min: 0 }"
				:getModelValue="() => getSpacingValue(null)"
				:getPlaceholder="getPlaceholder"
				:setModelValue="setSpacing"
				:getVariantValue="getSpacingValue"
				:setVariantValue="setVariantValue"
				@update:split="setSplitMode" />
		</div>
	</div>
</template>

<script lang="ts" setup>
import SplitModeInput from "@/components/Controls/SplitModeInput.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { normalizeValueWithUnits } from "@/utils/helpers";
import { computed, onMounted, ref } from "vue";

type SpacingType = "margin" | "padding";

const UNITS = ["px", "em", "rem"];
const SIDE_LABELS = ["T", "R", "B", "L"];

const props = defineProps<{ type: SpacingType }>();

const activeState = ref<string | null>(null);
const sidesLinked = ref(true);
const sideValues = ref(["0px", "0px", "0px", "0px"]);
const label = computed(() => (props.type === "margin" ? "Margin" : "Padding"));

const expandSpacing = (value: unknown): string[] => {
	const values = String(value ?? "").trim().split(/\s+/).filter(Boolean);
	if (!values.length) return ["0px", "0px", "0px", "0px"];
	if (values.length === 1) return Array(4).fill(values[0]);
	if (values.length === 2) return [values[0], values[1], values[0], values[1]];
	if (values.length === 3) return [values[0], values[1], values[2], values[1]];
	return values.slice(0, 4);
};

const getBaseValue = (cascading = false) =>
	props.type === "margin"
		? blockController.getMargin({ nativeOnly: !cascading, cascading })
		: blockController.getPadding({ nativeOnly: !cascading, cascading });

const getSpacingValue = (state: string | null) =>
	state ? String(blockController.getNativeStyle(`${state}:${props.type}`) ?? "") : String(getBaseValue());

const getPlaceholder = () => String(getBaseValue(true));

const syncSideValues = (value = getSpacingValue(activeState.value)) => {
	sideValues.value = expandSpacing(value);
	sidesLinked.value = new Set(sideValues.value).size === 1;
};

onMounted(() => syncSideValues());

const selectActiveState = (event: Event) => {
	const variantRow = (event.target as HTMLElement).closest("[data-variant]:not(input)");
	activeState.value = variantRow?.getAttribute("data-variant") || null;
	syncSideValues();
};

const setBaseValue = (value: string) => {
	if (props.type === "margin") blockController.setMargin(value);
	else blockController.setPadding(value);
};

const setSpacing = (value: string | number | boolean | null) => {
	const spacing = String(value || "");
	if (activeState.value) blockController.setStyle(`${activeState.value}:${props.type}`, value);
	else setBaseValue(spacing);
	sideValues.value = expandSpacing(spacing);
};

const normalizeSideValue = (value: string | number | boolean | null) =>
	normalizeValueWithUnits(String(value), UNITS, props.type);

const combineSpacingValues = (values: Array<string | number | boolean | null>) => values.join(" ");

const setSplitMode = (split: boolean) => {
	if (split) {
		sidesLinked.value = false;
		return;
	}
	setSpacing(sideValues.value[0]);
	sidesLinked.value = true;
};

const setVariantValue = (variant: string, value: string | number | boolean | null) => {
	activeState.value = variant;
	setSpacing(value);
};
</script>
