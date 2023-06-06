<template>
	<Popover transition="default" placement="left" class="w-full" popoverClass="!min-w-fit !mr-[30px]">
		<template #target="{ togglePopover, isOpen }">
			<div class="mb-2 flex items-center justify-between">
				<span class="inline-block text-[10px] font-medium text-gray-600 dark:text-zinc-400">
					{{ label }}
				</span>
				<div class="relative w-2/3">
					<div
						class="absolute left-[5px] top-[4px] z-20 h-5 w-5 cursor-pointer rounded-md shadow-sm"
						:style="{
							background: modelValue || 'white',
						}"
						@click="
							() => {
								togglePopover();
								setSelectorPosition();
							}
						"></div>
					<Input
						type="text"
						:value="modelValue"
						inputClass="pl-8 text-xs"
						:placeholder="placeholder"
						@change="setRGB" />
				</div>
			</div>
		</template>
		<template #body-main class="p-3">
			<div ref="colorPicker" class="p-3">
				<div
					ref="colorMap"
					:style="{
						background: `
							linear-gradient(0deg, black, transparent),
							linear-gradient(90deg, white, transparent),
							hsl(${hue}, 100%, 50%)
						`,
					}"
					@mousedown="handleSelectorMove"
					class="relative m-auto h-24 w-44 rounded-md"
					@click="setColor">
					<div
						ref="colorSelector"
						@mousedown="handleSelectorMove"
						class="absolute h-3 w-3 rounded-full border border-black border-opacity-20 before:absolute before:h-full before:w-full before:rounded-full before:border-2 before:border-white before:bg-[currentColor] after:absolute after:left-[2px] after:top-[2px] after:h-[calc(100%-4px)] after:w-[calc(100%-4px)] after:rounded-full after:border after:border-black after:border-opacity-20 after:bg-transparent"
						:style="{
							color: modelValue,
							background: 'transparent',
						}"></div>
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
						class="absolute h-3 w-3 rounded-full border border-[rgba(0,0,0,.2)] before:absolute before:h-full before:w-full before:rounded-full before:border-2 before:border-white before:bg-[currentColor] after:absolute after:left-[2px] after:top-[2px] after:h-[calc(100%-4px)] after:w-[calc(100%-4px)] after:rounded-full after:border after:border-[rgba(0,0,0,.2)] after:bg-transparent"
						:style="{
							color: `hsl(${hue}, 100%, 50%)`,
							background: 'transparent',
						}"></div>
				</div>
				<div ref="colorPalette">
					<div class="mt-3 flex flex-wrap gap-1">
						<div
							v-for="color in colors"
							:key="color"
							class="h-4 w-4 cursor-pointer rounded-full shadow-sm"
							:style="{
								background: color,
							}"></div>
					</div>
				</div>
			</div>
		</template>
	</Popover>
</template>
<script setup lang="ts">
import { HSVToHex, HexToHSV } from "@/utils/helpers";
import { Input, Popover } from "frappe-ui";
import { PropType, Ref, nextTick, ref } from "vue";
import { clamp } from "@vueuse/core";

const hueMap = ref(null) as unknown as Ref<HTMLDivElement>;
const colorMap = ref(null) as unknown as Ref<HTMLDivElement>;
const hueSelector = ref(null) as unknown as Ref<HTMLDivElement>;
const colorSelector = ref(null) as unknown as Ref<HTMLDivElement>;

const props = defineProps({
	label: {
		type: String,
		default: "",
	},
	modelValue: {
		type: String as PropType<HashString>,
	},
	placeholder: {
		type: String,
		default: "Set Color",
	},
});
const emit = defineEmits(["update:modelValue"]);
const hue = ref(0);

const colors = [
	"#FF6633",
	"#FFB399",
	"#FF33FF",
	"#00B3E6",
	"#E6B333",
	"#3366E6",
	"#999966",
	"#99FF99",
	"#B34D4D",
];

const setRGB = (rgb: HashString) => {
	emit("update:modelValue", rgb);
	setSelectorPosition();
};

const setColorSelectorPosition = () => {
	const colorSelectorBounds = colorSelector.value.getBoundingClientRect();
	let left = 0 - colorSelectorBounds.width / 2;
	let top = 0 - colorSelectorBounds.height / 2;
	if (props.modelValue) {
		const { width, height } = colorMap.value.getBoundingClientRect();
		const { s, v } = HexToHSV(props.modelValue as HashString);
		left = (s / 100) * width + left;
		top = ((100 - v) / 100) * height + top;
	}
	colorSelector.value.style.left = `${left}px`;
	colorSelector.value.style.top = `${top}px`;
};

const setHueSelectorPosition = () => {
	const hueSelectorBounds = hueSelector.value.getBoundingClientRect();
	let left = 0 - hueSelectorBounds.width / 2;
	if (props.modelValue) {
		const { width } = hueMap.value.getBoundingClientRect();
		const { h } = HexToHSV(props.modelValue as HashString);
		hue.value = h;
		left = (h / 360) * width + left;
		hueSelector.value.style.left = `${left}px`;
	}
	hueSelector.value.style.left = `${left}px`;
};

const handleSelectorMove = (ev: MouseEvent) => {
	setColor(ev);
	document.addEventListener("mousemove", setColor);
	document.addEventListener(
		"mouseup",
		(mouseUpEvent) => {
			document.removeEventListener("mousemove", setColor);
			mouseUpEvent.preventDefault();
		},
		{ once: true }
	);
};

const handleHueSelectorMove = (ev: MouseEvent) => {
	setHue(ev);
	document.addEventListener("mousemove", setHue);
	document.addEventListener(
		"mouseup",
		(mouseUpEvent) => {
			document.removeEventListener("mousemove", setHue);
			mouseUpEvent.preventDefault();
		},
		{ once: true }
	);
};

function setColor(ev: MouseEvent) {
	const clickPointX = ev.clientX;
	const clickPointY = ev.clientY;
	const colorSelectorBounds = colorSelector.value.getBoundingClientRect();
	const colorMapBounds = colorMap.value.getBoundingClientRect();

	let pointX = clickPointX - colorMapBounds.left;
	let pointY = clickPointY - colorMapBounds.top;

	pointX = clamp(pointX, 0, colorMapBounds.width);
	pointY = clamp(pointY, 0, colorMapBounds.height);

	const s = Math.round((pointX / colorMapBounds.width) * 100);
	const v = 100 - Math.round((pointY / colorMapBounds.height) * 100);
	const h = hue.value;

	const left = pointX - colorSelectorBounds.width / 2;
	const top = pointY - colorSelectorBounds.height / 2;

	emit("update:modelValue", HSVToHex(h, s, v));
	colorSelector.value.style.top = `${top}px`;
	colorSelector.value.style.left = `${left}px`;
}

function setHue(ev: MouseEvent) {
	const hueMapBounds = hueMap.value.getBoundingClientRect();
	const hueSelectorBounds = hueSelector.value.getBoundingClientRect();
	const { clientX } = ev;
	let point = clientX - hueMapBounds.left;
	point = clamp(point, 0, hueMapBounds.width);
	const x = point - hueSelectorBounds.width / 2;
	const h = Math.round((point / hueMapBounds.width) * 360);
	hue.value = h;
	hueSelector.value.style.left = `${x}px`;
}

function setSelectorPosition() {
	nextTick(() => {
		setColorSelectorPosition();
		setHueSelectorPosition();
	});
}
</script>
