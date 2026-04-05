<template>
	<Popover
		ref="colorPickerPopover"
		v-if="renderMode === 'popover'"
		:placement="placement"
		:offset="offset"
		class="!block w-full"
		popoverClass="!min-w-fit">
		<template #target="{ togglePopover, isOpen }">
			<slot
				name="target"
				:togglePopover="
					() => {
						togglePopover();
						setSelectorPosition(modelColor);
					}
				"
				:isOpen="isOpen"></slot>
		</template>
		<template #body="{ close }">
			<div
				ref="colorPicker"
				class="color-picker-container flex flex-col gap-2 rounded-lg bg-surface-white p-3 shadow-lg">
				<div
					ref="colorMap"
					:style="colorMapStyle"
					@mousedown.prevent="handleSelectorMove"
					class="relative m-auto h-24 w-full rounded-md"
					@click.prevent="setColor">
					<div
						ref="colorSelector"
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
					<div
						ref="hueSelector"
						@mousedown="handleHueSelectorMove"
						:class="hueSelectorClass"
						:style="hueSelectorStyle"></div>
				</div>
				<div
					ref="alphaMap"
					class="relative m-auto h-3 w-full rounded-md"
					@click="setAlpha"
					@mousedown.prevent="handleAlphaSelectorMove"
					:style="alphaMapStyle">
					<div
						@mousedown="handleAlphaSelectorMove"
						:class="hueSelectorClass"
						:style="alphaSelectorStyle"></div>
				</div>
				<div ref="colorPalette">
					<div class="flex flex-wrap gap-1.5">
						<div
							v-for="color in colors"
							:key="color"
							class="h-3.5 w-3.5 cursor-pointer rounded-full shadow-sm"
							@click="handleColorPaletteClick(color)"
							:style="{ background: color }"></div>
						<EyeDropperIcon v-if="isSupported" class="text-ink-gray-7" @click="() => open()" />
					</div>
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
	</Popover>
	<div
		v-else
		ref="colorPicker"
		:class="[
			'color-picker-container',
			renderMode === 'inline'
				? 'flex w-full flex-col gap-2'
				: 'flex flex-col gap-2 rounded-lg bg-surface-white p-3 shadow-lg',
		]">
		<div
			ref="colorMap"
			:style="colorMapStyle"
			@mousedown.prevent="handleSelectorMove"
			class="relative m-auto h-24 w-full rounded-md"
			@click.prevent="setColor">
			<div
				ref="colorSelector"
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
			<div
				ref="hueSelector"
				@mousedown="handleHueSelectorMove"
				:class="hueSelectorClass"
				:style="hueSelectorStyle"></div>
		</div>
		<div
			ref="alphaMap"
			class="relative m-auto h-3 w-full rounded-md"
			@click="setAlpha"
			@mousedown.prevent="handleAlphaSelectorMove"
			:style="alphaMapStyle">
			<div @mousedown="handleAlphaSelectorMove" :class="hueSelectorClass" :style="alphaSelectorStyle"></div>
		</div>
		<div ref="colorPalette">
			<div class="flex flex-wrap gap-1.5">
				<div
					v-for="color in colors"
					:key="color"
					class="h-3.5 w-3.5 cursor-pointer rounded-full shadow-sm"
					@click="handleColorPaletteClick(color)"
					:style="{ background: color }"></div>
				<EyeDropperIcon v-if="isSupported" class="text-ink-gray-7" @click="() => open()" />
			</div>
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
import { Popover } from "frappe-ui";
import { Ref, StyleValue, computed, nextTick, ref, watch } from "vue";

type CSSColorValue = HashString | RGBString | `var(--${string})`;

const { variables, resolveVariableValue } = useBuilderVariable();

const isDark = useDark({
	attribute: "data-theme",
});

const canvasStore = useCanvasStore();
const hueMap = ref(null) as unknown as Ref<HTMLDivElement>;
const colorMap = ref(null) as unknown as Ref<HTMLDivElement>;
const alphaMap = ref(null) as unknown as Ref<HTMLDivElement>;

const {
	width: colorMapWidth,
	height: colorMapHeight,
	left: colorMapLeft,
	top: colorMapTop,
} = useElementBounding(colorMap);
const { width: hueMapWidth, left: hueMapLeft } = useElementBounding(hueMap);
const { width: alphaMapWidth, left: alphaMapLeft } = useElementBounding(alphaMap);

const colorPickerPopover = ref<InstanceType<typeof Popover> | null>(null);

const colorSelectorPosition = ref({ x: 0, y: 0 });
const hueSelectorPosition = ref({ x: 0, y: 0 });
const alphaSelectorPosition = ref({ x: Infinity, y: 0 });
let currentColor = "#FFF" as HashString;

const { isSupported, sRGBHex, open } = useEyeDropper();

const props = withDefaults(
	defineProps<{
		modelValue?: CSSColorValue | null;
		showInput?: boolean;
		placement?:
			| "bottom-start"
			| "top-start"
			| "top-end"
			| "bottom-end"
			| "right-start"
			| "right-end"
			| "left-start"
			| "left-end"
			| "bottom"
			| "top"
			| "right"
			| "left";
		renderMode?: "popover" | "inline";
		offset?: number;
	}>(),
	{
		modelValue: null,
		showInput: false,
		placement: "left-start",
		renderMode: "popover",
		offset: 10,
	},
);

const modelColor = computed(() => {
	const color = props.modelValue;
	if (!color) return null;
	const resolvedColor = resolveVariableValue(color);
	return getRGB(resolvedColor);
});

const getOptions = async (query: string) => {
	return getColorVariableOptions(query, variables.value, resolveVariableValue, isDark.value);
};

const emit = defineEmits(["update:modelValue"]);

const colors = [
	"#FFB3E6",
	"#00B3E6",
	"#E6B333",
	"#3366E6",
	"#999966",
	"#99FF99",
	"#B34D4D",
	"#80B300",
] as HashString[];

if (!isSupported.value) {
	colors.push("#B34D4D");
}

const colorMapStyle = computed(() => ({
	background: `
		linear-gradient(0deg, black, transparent),
		linear-gradient(90deg, white, transparent),
		hsl(${hue.value}, 100%, 50%)
	`,
}));

const hueMapStyle = computed(() => ({
	background: `
		linear-gradient(90deg, hsl(0, 100%, 50%),
		hsl(60, 100%, 50%), hsl(120, 100%, 50%),
		hsl(180, 100%, 50%), hsl(240, 100%, 50%),
		hsl(300, 100%, 50%), hsl(360, 100%, 50%))
	`,
}));

const liveSolidColor = computed(() => {
	if (!colorMapWidth.value || !colorMapHeight.value) return `hsl(${hue.value}, 100%, 50%)`;
	const s = Math.round((colorSelectorPosition.value.x / colorMapWidth.value) * 100);
	const v = 100 - Math.round((colorSelectorPosition.value.y / colorMapHeight.value) * 100);
	return HSVToHex(hue.value, s, v) as string;
});

const alphaMapStyle = computed(() => {
	const solidColor = liveSolidColor.value;
	return {
		background: `
			linear-gradient(90deg, transparent, ${solidColor}),
			repeating-conic-gradient(#ccc 0% 25%, var(--surface-white) 0% 50%) 0 0 / 8px 8px
		`,
	};
});

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

const handleColorPaletteClick = (color: HashString) => {
	setSelectorPosition(color);
	updateColor();
};

const handleInputChange = (color: string | null) => {
	if (!color) {
		emit("update:modelValue", null);
		return;
	}

	if (color.startsWith("var(--") || color.startsWith("--")) {
		emit("update:modelValue", color.startsWith("var(--") ? color : `var(${color})`);
		return;
	}

	setSelectorPosition(color as HashString);
	updateColor();
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
		return;
	}
	const resolvedColor = resolveVariableValue(color);
	nextTick(() => {
		setColorSelectorPosition(resolvedColor);
		setHueSelectorPosition(resolvedColor);
		setAlphaSelectorPosition(resolvedColor);
		currentColor = resolvedColor as HashString;
	});
}

const hue = computed(() => {
	const positionX = hueSelectorPosition.value.x || 0;
	return Math.round((positionX / (hueMapWidth.value || 1)) * 360);
});

const alpha = computed(() => {
	const positionX = clamp(alphaSelectorPosition.value.x, 0, alphaMapWidth.value || 1);
	return Math.round((positionX / (alphaMapWidth.value || 1)) * 100);
});

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

function togglePopover(open?: boolean) {
	if (open === undefined || open) {
		colorPickerPopover.value?.open();
	} else {
		colorPickerPopover.value?.close();
	}
}

defineExpose({
	togglePopover,
});
</script>
