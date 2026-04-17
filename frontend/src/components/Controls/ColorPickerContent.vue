<template>
	<div
		:class="[
			'color-picker-container flex flex-col gap-2',
			renderMode === 'inline' ? 'w-full' : 'rounded-lg bg-surface-white p-3 shadow-lg',
		]">
		<div
			ref="colorMap"
			:style="colorMapStyle"
			@mousedown.prevent="handleSelectorMove"
			class="relative m-auto h-24 w-full rounded-md"
			@click.prevent="setColor">
			<div
				@mousedown.stop.prevent="handleSelectorMove"
				:class="selectorClass"
				:style="colorSelectorStyle"></div>
		</div>
		<div
			ref="hueMap"
			class="relative m-auto h-3 w-full rounded-md"
			@click="setHue"
			@mousedown.prevent="handleHueSelectorMove"
			:style="hueMapStyle">
			<div @mousedown="handleHueSelectorMove" :class="hueSelectorClass" :style="hueSelectorStyle"></div>
		</div>
		<div
			ref="alphaMap"
			class="relative m-auto h-3 w-full rounded-md"
			@click="setAlpha"
			@mousedown.prevent="handleAlphaSelectorMove"
			:style="alphaMapStyle">
			<div @mousedown="handleAlphaSelectorMove" :class="hueSelectorClass" :style="alphaSelectorStyle"></div>
		</div>
		<div class="flex flex-wrap gap-1.5">
			<div
				v-for="color in colors"
				:key="color"
				class="h-3.5 w-3.5 cursor-pointer rounded-full shadow-sm"
				@click="selectColor(color)"
				:style="{ background: color }"></div>
			<EyeDropperIcon v-if="isSupported" class="text-ink-gray-7" @click="() => open()" />
		</div>
		<Autocomplete
			v-if="showInput"
			:modelValue="modelValue"
			class="mt-2 w-full text-sm [&>div>div>input]:text-sm"
			placeholder="Set Color"
			:getOptions="getOptions"
			referenceElementSelector=".color-picker-container"
			@update:modelValue="handleInputChange" />
	</div>
</template>
<script setup lang="ts">
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import EyeDropperIcon from "@/components/Icons/EyeDropper.vue";
import useCanvasStore from "@/stores/canvasStore";
import { getColorVariableOptions } from "@/utils/colorOptions";
import { HSVToHex, HexToHSV, getRGB } from "@/utils/helpers";
import { useBuilderVariable } from "@/utils/useBuilderVariable";
import { clamp, useDark, useElementBounding, useEyeDropper } from "@vueuse/core";
import { Ref, StyleValue, computed, nextTick, ref, watch } from "vue";

type CSSColorValue = HashString | RGBString | `var(--${string})`;

const { variables, resolveVariableValue } = useBuilderVariable();
const isDark = useDark({ attribute: "data-theme" });
const canvasStore = useCanvasStore();

const colorMap = ref(null) as unknown as Ref<HTMLDivElement>;
const hueMap = ref(null) as unknown as Ref<HTMLDivElement>;
const alphaMap = ref(null) as unknown as Ref<HTMLDivElement>;

const {
	width: colorMapWidth,
	height: colorMapHeight,
	left: colorMapLeft,
	top: colorMapTop,
} = useElementBounding(colorMap);
const { width: hueMapWidth, left: hueMapLeft } = useElementBounding(hueMap);
const { width: alphaMapWidth, left: alphaMapLeft } = useElementBounding(alphaMap);

const colorSelectorPosition = ref({ x: 0, y: 0 });
const hueSelectorPosition = ref({ x: 0, y: 0 });
const alphaSelectorPosition = ref({ x: Infinity, y: 0 });
let currentColor = "#FFF" as HashString;
let pendingPositionColor: string | null = null;

watch(colorMapWidth, (w) => {
	if (w && pendingPositionColor) {
		const color = pendingPositionColor;
		nextTick(() => {
			setColorSelectorPosition(color);
			setHueSelectorPosition(color);
			setAlphaSelectorPosition(color);
		});
	}
});

const { isSupported, sRGBHex, open } = useEyeDropper();

const props = withDefaults(
	defineProps<{
		modelValue?: CSSColorValue | null;
		showInput?: boolean;
		renderMode?: "popover" | "inline";
	}>(),
	{ modelValue: null, showInput: false, renderMode: "popover" },
);

const modelColor = computed(() => {
	const color = props.modelValue;
	if (!color) return null;
	return getRGB(resolveVariableValue(color));
});

const getOptions = async (query: string) =>
	getColorVariableOptions(query, variables.value, resolveVariableValue, isDark.value);

const emit = defineEmits(["update:modelValue"]);

const colors: HashString[] = [
	"#FFB3E6",
	"#00B3E6",
	"#E6B333",
	"#3366E6",
	"#999966",
	"#99FF99",
	"#B34D4D",
	"#80B300",
];
if (!isSupported.value) colors.push("#B34D4D");

const hue = computed(() => Math.round(((hueSelectorPosition.value.x || 0) / (hueMapWidth.value || 1)) * 360));
const alpha = computed(() =>
	Math.round(
		(clamp(alphaSelectorPosition.value.x, 0, alphaMapWidth.value || 1) / (alphaMapWidth.value || 1)) * 100,
	),
);

const liveSolidColor = computed(() => {
	if (!colorMapWidth.value || !colorMapHeight.value) return `hsl(${hue.value}, 100%, 50%)`;
	const s = Math.round((colorSelectorPosition.value.x / colorMapWidth.value) * 100);
	const v = 100 - Math.round((colorSelectorPosition.value.y / colorMapHeight.value) * 100);
	return HSVToHex(hue.value, s, v) as string;
});

const colorMapStyle = computed(() => ({
	background: `linear-gradient(0deg, black, transparent), linear-gradient(90deg, white, transparent), hsl(${hue.value}, 100%, 50%)`,
}));

const hueMapStyle = computed(() => ({
	background: `linear-gradient(90deg, hsl(0,100%,50%), hsl(60,100%,50%), hsl(120,100%,50%), hsl(180,100%,50%), hsl(240,100%,50%), hsl(300,100%,50%), hsl(360,100%,50%))`,
}));

const alphaMapStyle = computed(() => ({
	background: `linear-gradient(90deg, transparent, ${liveSolidColor.value}), repeating-conic-gradient(#ccc 0% 25%, var(--surface-white) 0% 50%) 0 0 / 8px 8px`,
}));

const selectorClass =
	"absolute rounded-full border border-black border-opacity-20 before:absolute before:h-full before:w-full before:rounded-full before:border-2 before:border-white before:!bg-[currentColor] after:absolute after:left-[2px] after:top-[2px] after:h-[calc(100%-4px)] after:w-[calc(100%-4px)] after:rounded-full after:border after:border-black after:border-opacity-20 after:bg-transparent";
const hueSelectorClass =
	"absolute rounded-full border border-[rgba(0,0,0,.2)] before:absolute before:h-full before:w-full before:rounded-full before:border-2 before:border-white before:bg-[currentColor] after:absolute after:left-[2px] after:top-[2px] after:h-[calc(100%-4px)] after:w-[calc(100%-4px)] after:rounded-full after:border after:border-[rgba(0,0,0,.2)] after:bg-transparent";

const colorSelectorStyle = computed(
	() =>
		({
			height: "12px",
			width: "12px",
			left: `calc(${colorSelectorPosition.value.x}px - 6px)`,
			top: `calc(${colorSelectorPosition.value.y}px - 6px)`,
			color: liveSolidColor.value,
			background: "transparent",
		}) as StyleValue,
);

const hueSelectorStyle = computed(() => ({
	height: "12px",
	width: "12px",
	left: `calc(${hueSelectorPosition.value.x}px - 6px)`,
	color: `hsl(${hue.value}, 100%, 50%)`,
	background: "transparent",
}));

const alphaSelectorStyle = computed(() => {
	const alphaByte = Math.round((alpha.value / 100) * 255);
	const colorWithAlpha =
		alphaByte < 255
			? (`${liveSolidColor.value}${alphaByte.toString(16).padStart(2, "0")}` as HashString)
			: liveSolidColor.value;
	return {
		height: "12px",
		width: "12px",
		left: `calc(${clamp(alphaSelectorPosition.value.x, 0, alphaMapWidth.value)}px - 6px)`,
		color: colorWithAlpha,
		background: "transparent",
	};
});

const selectColor = (color: HashString) => {
	setSelectorPosition(color);
	updateColor();
};

const handleInputChange = (color: string | null) => {
	if (!color) return emit("update:modelValue", null);
	if (color.startsWith("var(--") || color.startsWith("--"))
		return emit("update:modelValue", color.startsWith("var(--") ? color : `var(${color})`);
	selectColor(color as HashString);
};

const setColorSelectorPosition = (color: string) => {
	if (!colorMapWidth.value || !colorMapHeight.value) return;
	const { s, v } = HexToHSV(color as HashString);
	colorSelectorPosition.value = {
		x: clamp(s * colorMapWidth.value, 0, colorMapWidth.value),
		y: clamp((1 - v) * colorMapHeight.value, 0, colorMapHeight.value),
	};
};

const setHueSelectorPosition = (color: string) => {
	if (!hueMapWidth.value) return;
	const { h } = HexToHSV(color as HashString);
	hueSelectorPosition.value = { x: (h / 360) * hueMapWidth.value, y: 0 };
};

const setAlphaSelectorPosition = (color: string) => {
	if (!alphaMapWidth.value) return;
	const { a } = HexToHSV(color as HashString);
	alphaSelectorPosition.value = { x: (a / 100) * alphaMapWidth.value, y: 0 };
};

function makeDragHandler(setter: (ev: MouseEvent) => void) {
	return (ev: MouseEvent) => {
		setter(ev);
		const pauseId = canvasStore.activeCanvas?.history?.pause();
		const onMove = (e: MouseEvent) => {
			e.preventDefault();
			setter(e);
		};
		document.addEventListener("mousemove", onMove);
		document.addEventListener(
			"mouseup",
			(e) => {
				document.removeEventListener("mousemove", onMove);
				e.preventDefault();
				pauseId && canvasStore.activeCanvas?.history?.resume(pauseId, true);
			},
			{ once: true },
		);
	};
}

const handleSelectorMove = makeDragHandler(setColor);
const handleHueSelectorMove = makeDragHandler(setHue);
const handleAlphaSelectorMove = makeDragHandler(setAlpha);

function setColor(ev: MouseEvent) {
	colorSelectorPosition.value = {
		x: clamp(ev.clientX - colorMapLeft.value, 0, colorMapWidth.value),
		y: clamp(ev.clientY - colorMapTop.value, 0, colorMapHeight.value),
	};
	updateColor();
}

function setHue(ev: MouseEvent) {
	hueSelectorPosition.value = { x: clamp(ev.clientX - hueMapLeft.value, 0, hueMapWidth.value), y: 0 };
	updateColor();
}

function setAlpha(ev: MouseEvent) {
	alphaSelectorPosition.value = { x: clamp(ev.clientX - alphaMapLeft.value, 0, alphaMapWidth.value), y: 0 };
	updateColor();
}

function setSelectorPosition(color: HashString | null) {
	if (!color) {
		colorSelectorPosition.value = { x: 0, y: 0 };
		hueSelectorPosition.value = { x: 0, y: 0 };
		alphaSelectorPosition.value = { x: Infinity, y: 0 };
		pendingPositionColor = null;
		return;
	}
	const resolvedColor = resolveVariableValue(color);
	pendingPositionColor = resolvedColor;
	nextTick(() => {
		setColorSelectorPosition(resolvedColor);
		setHueSelectorPosition(resolvedColor);
		setAlphaSelectorPosition(resolvedColor);
		currentColor = resolvedColor as HashString;
	});
}

const updateColor = () => {
	nextTick(() => {
		if (!colorMapWidth.value || !colorMapHeight.value) return;
		const s = Math.round((colorSelectorPosition.value.x / colorMapWidth.value) * 100);
		const v = 100 - Math.round((colorSelectorPosition.value.y / colorMapHeight.value) * 100);
		currentColor = HSVToHex(hue.value, s, v, alpha.value);
		emit("update:modelValue", currentColor);
	});
};

watch(sRGBHex, () => {
	if (!isSupported.value || !sRGBHex.value) return;
	emit("update:modelValue", sRGBHex.value);
});

watch(
	() => props.modelValue,
	(color) => {
		if (color === currentColor) return;
		setSelectorPosition(getRGB(color));
	},
	{ immediate: true },
);

defineExpose({ syncPositions: () => setSelectorPosition(modelColor.value) });
</script>
