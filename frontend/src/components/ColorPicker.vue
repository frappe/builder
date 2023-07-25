<template>
	<Popover transition="default" placement="left" class="!block w-full" popoverClass="!min-w-fit !mr-[30px]">
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
		<template #body>
			<div ref="colorPicker" class="rounded-lg bg-white p-3 shadow-lg dark:bg-zinc-900">
				<div
					ref="colorMap"
					:style="{
						background: `
							linear-gradient(0deg, black, transparent),
							linear-gradient(90deg, white, transparent),
							hsl(${hue}, 100%, 50%)
						`,
					}"
					@mousedown.stop="handleSelectorMove"
					class="relative m-auto h-24 w-44 rounded-md"
					@click.prevent="setColor">
					<div
						ref="colorSelector"
						@mousedown.stop="handleSelectorMove"
						class="absolute rounded-full border border-black border-opacity-20 before:absolute before:h-full before:w-full before:rounded-full before:border-2 before:border-white before:bg-[currentColor] after:absolute after:left-[2px] after:top-[2px] after:h-[calc(100%-4px)] after:w-[calc(100%-4px)] after:rounded-full after:border after:border-black after:border-opacity-20 after:bg-transparent"
						:style="{
							height: '12px',
							width: '12px',
							left: `calc(${colorSelectorPosition.x}px - 6px)`,
							top: `calc(${colorSelectorPosition.y}px - 6px)`,
							color: modelColor,
							background: 'transparent',
						} as StyleValue"></div>
				</div>
				<div
					ref="hueMap"
					class="relative m-auto mt-2 h-3 w-44 rounded-md"
					@click="setHue"
					@mousedown="handleHueSelectorMove"
					:style="{
						background: `
							linear-gradient(90deg, hsl(0, 100%, 50%),
							hsl(60, 100%, 50%), hsl(120, 100%, 50%),
							hsl(180, 100%, 50%), hsl(240, 100%, 50%),
							hsl(300, 100%, 50%), hsl(360, 100%, 50%))
						`,
					}">
					<div
						ref="hueSelector"
						@mousedown="handleHueSelectorMove"
						class="absolute rounded-full border border-[rgba(0,0,0,.2)] before:absolute before:h-full before:w-full before:rounded-full before:border-2 before:border-white before:bg-[currentColor] after:absolute after:left-[2px] after:top-[2px] after:h-[calc(100%-4px)] after:w-[calc(100%-4px)] after:rounded-full after:border after:border-[rgba(0,0,0,.2)] after:bg-transparent"
						:style="{
							height: '12px',
							width: '12px',
							left: `calc(${hueSelectorPosition.x}px - 6px)`,
							color: `hsl(${hue}, 100%, 50%)`,
							background: 'transparent',
						}"></div>
				</div>
				<div ref="colorPalette">
					<div class="mt-3 flex flex-wrap gap-1.5">
						<div
							v-for="color in colors"
							:key="color"
							class="h-3.5 w-3.5 cursor-pointer rounded-full shadow-sm"
							@click="
								() => {
									setSelectorPosition(color);
									updateColor();
								}
							"
							:style="{
								background: color,
							}"></div>
						<svg
							v-if="isSupported"
							class="text-gray-700 dark:text-zinc-300"
							@click="() => open()"
							xmlns="http://www.w3.org/2000/svg"
							width="16"
							height="16"
							viewBox="0 0 24 24">
							<g fill="none" fill-rule="evenodd">
								<path
									d="M24 0v24H0V0h24ZM12.593 23.258l-.011.002l-.071.035l-.02.004l-.014-.004l-.071-.035c-.01-.004-.019-.001-.024.005l-.004.01l-.017.428l.005.02l.01.013l.104.074l.015.004l.012-.004l.104-.074l.012-.016l.004-.017l-.017-.427c-.002-.01-.009-.017-.017-.018Zm.265-.113l-.013.002l-.185.093l-.01.01l-.003.011l.018.43l.005.012l.008.007l.201.093c.012.004.023 0 .029-.008l.004-.014l-.034-.614c-.003-.012-.01-.02-.02-.022Zm-.715.002a.023.023 0 0 0-.027.006l-.006.014l-.034.614c0 .012.007.02.017.024l.015-.002l.201-.093l.01-.008l.004-.011l.017-.43l-.003-.012l-.01-.01l-.184-.092Z" />
								<path
									fill="currentColor"
									d="M20.477 3.511a3 3 0 0 0-4.243 0l-1.533 1.533a2.991 2.991 0 0 0-3.41.581l-.713.714a2 2 0 0 0 0 2.829l-6.486 6.485a3 3 0 0 0-.878 2.122v1.8a1.2 1.2 0 0 0 1.2 1.2h1.8a3 3 0 0 0 2.12-.88l6.486-6.484a2 2 0 0 0 2.829 0l.714-.715a2.991 2.991 0 0 0 .581-3.41l1.533-1.532a3 3 0 0 0 0-4.243ZM5.507 17.067l6.485-6.485l1.414 1.414l-6.485 6.486a1 1 0 0 1-.707.293h-1v-1a1 1 0 0 1 .293-.707Z" />
							</g>
						</svg>
					</div>
				</div>
			</div>
		</template>
	</Popover>
</template>
<script setup lang="ts">
import { HSVToHex, HexToHSV, RGBToHex, getRGB } from "@/utils/helpers";
import { clamp, useEyeDropper } from "@vueuse/core";
import { Popover } from "frappe-ui";
import { PropType, Ref, StyleValue, computed, nextTick, ref, watch } from "vue";

const hueMap = ref(null) as unknown as Ref<HTMLDivElement>;
const colorMap = ref(null) as unknown as Ref<HTMLDivElement>;
const hueSelector = ref(null) as unknown as Ref<HTMLDivElement>;
const colorSelector = ref(null) as unknown as Ref<HTMLDivElement>;

const colorSelectorPosition = ref({ x: 0, y: 0 });
const hueSelectorPosition = ref({ x: 0, y: 0 });
let currentColor = "#FFF" as HashString;

const { isSupported, sRGBHex, open } = useEyeDropper();

const props = defineProps({
	modelValue: {
		type: String as PropType<HashString | RGBString | null>,
		default: null,
	},
});

const modelColor = computed(() => {
	return getRGB(props.modelValue);
});

const emit = defineEmits(["update:modelValue"]);

const colors = [
	"#FF6633",
	"#FFB399",
	"#FF33FF",
	"#00B3E6",
	"#E6B333",
	"#3366E6",
	"#999966",
	"#99FF99",
] as HashString[];

if (!isSupported.value) {
	colors.push("#B34D4D");
}

const setColorSelectorPosition = (color: HashString) => {
	const { width, height } = colorMap.value.getBoundingClientRect();
	const { s, v } = HexToHSV(color);
	let x = clamp(s * width, 0, width);
	let y = clamp((1 - v) * height, 0, height);
	colorSelectorPosition.value = { x, y };
};

const setHueSelectorPosition = (color: HashString) => {
	const { width } = hueMap.value.getBoundingClientRect();
	const { h } = HexToHSV(color);
	const left = (h / 360) * width;
	hueSelectorPosition.value = { x: left, y: 0 };
};

const handleSelectorMove = (ev: MouseEvent) => {
	setColor(ev);
	const mouseMove = (mouseMoveEvent: MouseEvent) => {
		mouseMoveEvent.preventDefault();
		setColor(mouseMoveEvent);
	};
	document.addEventListener("mousemove", mouseMove);
	document.addEventListener(
		"mouseup",
		(mouseUpEvent) => {
			document.removeEventListener("mousemove", mouseMove);
			mouseUpEvent.preventDefault();
		},
		{ once: true }
	);
};

const handleHueSelectorMove = (ev: MouseEvent) => {
	setHue(ev);
	const mouseMove = (mouseMoveEvent: MouseEvent) => {
		mouseMoveEvent.preventDefault();
		setHue(mouseMoveEvent);
	};
	document.addEventListener("mousemove", mouseMove);
	document.addEventListener(
		"mouseup",
		(mouseUpEvent) => {
			document.removeEventListener("mousemove", mouseMove);
			mouseUpEvent.preventDefault();
		},
		{ once: true }
	);
};

function setColor(ev: MouseEvent) {
	const clickPointX = ev.clientX;
	const clickPointY = ev.clientY;
	const colorMapBounds = colorMap.value.getBoundingClientRect();

	let pointX = clickPointX - colorMapBounds.left;
	let pointY = clickPointY - colorMapBounds.top;

	pointX = clamp(pointX, 0, colorMapBounds.width);
	pointY = clamp(pointY, 0, colorMapBounds.height);
	colorSelectorPosition.value = { x: pointX, y: pointY };
	updateColor();
}

function setHue(ev: MouseEvent) {
	const hueMapBounds = hueMap.value.getBoundingClientRect();
	const { clientX } = ev;
	let point = clientX - hueMapBounds.left;
	point = clamp(point, 0, hueMapBounds.width);
	hueSelectorPosition.value = { x: point, y: 0 };
	updateColor();
}

function setSelectorPosition(color: HashString | null) {
	if (!color) return;
	nextTick(() => {
		setColorSelectorPosition(color);
		setHueSelectorPosition(color);
	});
}

const hue = computed(() => {
	if (!hueMap.value) return 0;
	const positionX = hueSelectorPosition.value.x || 0;
	const width = hueMap.value.getBoundingClientRect().width || 1;
	return Math.round((positionX / width) * 360);
});

const updateColor = () => {
	nextTick(() => {
		const colorMapBounds = colorMap.value.getBoundingClientRect();
		const s = Math.round((colorSelectorPosition.value.x / colorMapBounds.width) * 100);
		const v = 100 - Math.round((colorSelectorPosition.value.y / colorMapBounds.height) * 100);
		const h = hue.value;
		currentColor = HSVToHex(h, s, v);
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
	{ immediate: true }
);
</script>
