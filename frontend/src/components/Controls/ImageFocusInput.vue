<template>
	<div ref="rootRef" class="flex flex-col gap-1.5">
		<div v-if="label" class="flex items-center justify-between">
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
			class="relative mx-auto cursor-crosshair overflow-hidden rounded border border-outline-gray-2 bg-surface-gray-1"
			:class="[boxSize ? '' : 'h-24 w-full', dragging && 'is-dragging']"
			:style="boxSize || {}"
			@mousedown="onBoxMouseDown">
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
			<slot />
		</div>
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import useCanvasStore from "@/stores/canvasStore";
import { __ } from "@/translation";
import type { PauseId } from "@/utils/useCanvasHistory";
import { useElementSize, useMouseInElement } from "@vueuse/core";
import { computed, ref } from "vue";

const props = defineProps<{
	modelValue?: string;
	imageSrc: string;
	label?: string;
}>();

const emit = defineEmits(["update:modelValue"]);

const canvasStore = useCanvasStore();

const rootRef = ref<HTMLElement | null>(null);
const boxRef = ref<HTMLElement | null>(null);
const imgRef = ref<HTMLImageElement | null>(null);
const natural = ref<{ w: number; h: number } | null>(null);

const onLoad = () => {
	const img = imgRef.value;
	if (img?.naturalWidth) natural.value = { w: img.naturalWidth, h: img.naturalHeight };
};

const { width: boxWidth, height: boxHeight } = useElementSize(boxRef);
const { width: rootWidth } = useElementSize(rootRef);

// the box hugs the image's own aspect ratio (height-capped) so a portrait
// photo doesn't sit in a letterboxed band with dead space either side
const MAX_BOX_H = 176;
const boxSize = computed(() => {
	if (!natural.value || !rootWidth.value) return null;
	const ratio = natural.value.w / natural.value.h;
	const w = Math.min(rootWidth.value, MAX_BOX_H * ratio);
	return { width: `${Math.round(w)}px`, height: `${Math.round(w / ratio)}px` };
});

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

const dragging = ref(false);
let pauseId: PauseId | undefined = undefined;

// a press on a slotted chip (upload/reset) is a click, never a drag
function onBoxMouseDown(e: MouseEvent) {
	if ((e.target as HTMLElement).closest("button")) return;
	e.preventDefault();
	dragging.value = true;
	pauseId = canvasStore.activeCanvas?.history?.pause();
	setFromPointer();
	const onMove = () => setFromPointer();
	document.addEventListener("mousemove", onMove);
	document.addEventListener(
		"mouseup",
		() => {
			document.removeEventListener("mousemove", onMove);
			dragging.value = false;
			if (pauseId) {
				canvasStore.activeCanvas?.history?.resume(pauseId, true);
				pauseId = undefined;
			}
		},
		{ once: true },
	);
}

function setFromPointer() {
	const rect = imageRect.value;
	if (!rect) return;
	const x = Math.round(Math.min(100, Math.max(0, ((elementX.value - rect.x) / rect.w) * 100)));
	const y = Math.round(Math.min(100, Math.max(0, ((elementY.value - rect.y) / rect.h) * 100)));
	emit("update:modelValue", `${x}% ${y}%`);
}
</script>
