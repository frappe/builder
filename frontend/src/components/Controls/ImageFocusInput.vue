<template>
	<div class="flex flex-col gap-1.5">
		<div class="flex items-center justify-between">
			<InputLabel>{{ label }}</InputLabel>
			<button
				v-if="hasCustomValue"
				type="button"
				class="text-xs text-ink-gray-5 transition-colors hover:text-ink-gray-7"
				@click="emit('update:modelValue', '')">
				{{ __("Reset") }}
			</button>
		</div>
		<div
			ref="boxRef"
			class="relative h-32 w-full cursor-crosshair overflow-hidden rounded border border-outline-gray-2 bg-surface-gray-1">
			<img
				ref="imgRef"
				:src="imageSrc"
				class="pointer-events-none h-full w-full select-none object-contain"
				draggable="false"
				@load="onLoad" />
			<div
				v-if="imageRect"
				class="pointer-events-none absolute size-3 rounded-full border-2 border-white shadow-[0_0_0_1.5px_rgba(0,0,0,0.45)]"
				:style="dotStyle" />
		</div>
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import useCanvasStore from "@/stores/canvasStore";
import { __ } from "@/translation";
import type { PauseId } from "@/utils/useCanvasHistory";
import { useElementSize, useMouseInElement, useMousePressed } from "@vueuse/core";
import { computed, ref, watch } from "vue";

const props = defineProps<{
	modelValue?: string;
	imageSrc: string;
	label?: string;
}>();

const emit = defineEmits(["update:modelValue"]);

const canvasStore = useCanvasStore();

const boxRef = ref<HTMLElement | null>(null);
const imgRef = ref<HTMLImageElement | null>(null);
const natural = ref<{ w: number; h: number } | null>(null);

const onLoad = () => {
	const img = imgRef.value;
	if (img?.naturalWidth) natural.value = { w: img.naturalWidth, h: img.naturalHeight };
};

const { width: boxWidth, height: boxHeight } = useElementSize(boxRef);

// where the object-contain image actually renders inside the box (it letterboxes)
const imageRect = computed(() => {
	if (!natural.value || !boxWidth.value || !boxHeight.value) return null;
	const scale = Math.min(boxWidth.value / natural.value.w, boxHeight.value / natural.value.h);
	const w = natural.value.w * scale;
	const h = natural.value.h * scale;
	return { w, h, x: (boxWidth.value - w) / 2, y: (boxHeight.value - h) / 2 };
});

const KEYWORDS: Record<string, number> = { left: 0, top: 0, center: 50, right: 100, bottom: 100 };

const point = computed(() => {
	const parts = (props.modelValue || "").trim().split(/\s+/).filter(Boolean);
	const parse = (part: string | undefined) => {
		if (!part) return 50;
		if (part.endsWith("%")) {
			const n = parseFloat(part);
			return isNaN(n) ? 50 : Math.min(100, Math.max(0, n));
		}
		return KEYWORDS[part] ?? 50;
	};
	// a lone vertical keyword ("top") names the y axis
	if (parts.length === 1 && (parts[0] === "top" || parts[0] === "bottom")) {
		return { x: 50, y: KEYWORDS[parts[0]] };
	}
	return { x: parse(parts[0]), y: parse(parts[1]) };
});

const hasCustomValue = computed(() => Boolean((props.modelValue || "").trim()));

const dotStyle = computed(() => {
	const rect = imageRect.value;
	if (!rect) return {};
	return {
		left: `${rect.x + (point.value.x / 100) * rect.w}px`,
		top: `${rect.y + (point.value.y / 100) * rect.h}px`,
		transform: "translate(-50%, -50%)",
	};
});

const { elementX, elementY } = useMouseInElement(boxRef);
const { pressed } = useMousePressed({ target: boxRef });

let pauseId: PauseId | undefined = undefined;

watch(pressed, (down) => {
	const history = canvasStore.activeCanvas?.history;
	if (down) {
		pauseId = history?.pause();
		setFromPointer();
	} else if (pauseId) {
		history?.resume(pauseId, true);
		pauseId = undefined;
	}
});

watch([elementX, elementY], () => {
	if (pressed.value) setFromPointer();
});

function setFromPointer() {
	const rect = imageRect.value;
	if (!rect) return;
	const x = Math.round(Math.min(100, Math.max(0, ((elementX.value - rect.x) / rect.w) * 100)));
	const y = Math.round(Math.min(100, Math.max(0, ((elementY.value - rect.y) / rect.h) * 100)));
	emit("update:modelValue", `${x}% ${y}%`);
}
</script>
