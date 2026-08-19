<template>
	<div ref="rootRef" class="flex flex-col gap-2">
		<!-- chips slot beside the clipped box, not inside it, so they can straddle
		     its edges without being cut by overflow-hidden -->
		<div
			class="relative mx-auto"
			:class="[boxSize ? '' : 'h-24 w-full', dragging && 'is-dragging']"
			:style="boxSize || {}">
			<div
				ref="boxRef"
				class="relative h-full w-full overflow-hidden rounded border border-outline-gray-2 bg-surface-gray-1"
				:class="disabled ? '' : 'cursor-crosshair'"
				@mousedown="onBoxMouseDown">
				<img
					ref="imgRef"
					:src="imageSrc"
					class="pointer-events-none h-full w-full select-none"
					:style="{ objectFit: disabled ? props.fit || 'contain' : 'contain' }"
					draggable="false"
					@load="onLoad" />
				<div
					v-if="!disabled && cropRectStyle"
					class="pointer-events-none absolute rounded-[2px] border border-white/90 shadow-[0_0_0_9999px_rgba(0,0,0,0.35)]"
					:style="cropRectStyle" />
				<div
					v-if="!disabled && imageRect"
					class="pointer-events-none absolute size-3 rounded-full border-2 border-white shadow-[0_0_0_1.5px_rgba(0,0,0,0.45)]"
					:style="dotStyle" />
			</div>
			<slot />
		</div>
		<div v-if="!disabled && viewBox !== undefined && natural" class="flex items-center gap-1.5">
			<Button
				variant="ghost"
				icon="zoom-out"
				:title="__('Zoom out')"
				:disabled="zoom <= 1"
				@click="stepZoom(-1)" />
			<RangeInput
				class="w-full"
				hideInput
				:modelValue="zoom"
				:min="1"
				:max="4"
				:step="0.05"
				@update:modelValue="(v: string | number) => emitViewBoxAt(Number(v), point.x, point.y)" />
			<Button
				variant="ghost"
				icon="zoom-in"
				:title="__('Zoom in')"
				:disabled="zoom >= 4"
				@click="stepZoom(1)" />
		</div>
	</div>
</template>

<script setup lang="ts">
import RangeInput from "@/components/Controls/RangeInput.vue";
import useCanvasStore from "@/stores/canvasStore";
import { Button } from "frappe-ui";
import { __ } from "@/translation";
import type { PauseId } from "@/utils/useCanvasHistory";
import { useElementSize, useMouseInElement } from "@vueuse/core";
import { computed, nextTick, onMounted, ref, watch } from "vue";

const props = defineProps<{
	modelValue?: string;
	imageSrc: string;
	label?: string;
	// objectViewBox inset; pass it (even empty) to get the zoom-crop slider
	viewBox?: string;
	// aspect ratio of the element the image fills; draws the visible-part frame
	targetRatio?: number;
	// plain preview: no dot, frame, hint, or zoom (non-cover fits)
	disabled?: boolean;
	// the actual object-fit, so the plain preview mirrors what the element shows
	fit?: string;
}>();

const emit = defineEmits(["update:modelValue", "update:viewBox"]);

const canvasStore = useCanvasStore();

const rootRef = ref<HTMLElement | null>(null);
const boxRef = ref<HTMLElement | null>(null);
const imgRef = ref<HTMLImageElement | null>(null);
const natural = ref<{ w: number; h: number } | null>(null);

const onLoad = () => {
	const img = imgRef.value;
	if (img?.naturalWidth) natural.value = { w: img.naturalWidth, h: img.naturalHeight };
};

// a cached image can be complete before the load listener attaches; without this
// the box never learns the ratio and falls back to the letterboxed strip
onMounted(onLoad);
watch(
	() => props.imageSrc,
	() => {
		natural.value = null;
		void nextTick(onLoad);
	},
);

const { width: boxWidth, height: boxHeight } = useElementSize(boxRef);
const { width: rootWidth } = useElementSize(rootRef);

// the box hugs the image's own aspect ratio (height-capped) so a portrait
// photo doesn't sit in a letterboxed band with dead space either side
const MAX_BOX_H = 176;
const boxSize = computed(() => {
	if (!rootWidth.value) return null;
	// a plain preview stretches across the card at a steady height, drawn with the
	// element's fit — the interactive surface shows the whole image at its own ratio
	if (props.disabled) {
		return { width: `${Math.round(rootWidth.value)}px`, height: `${MAX_BOX_H}px` };
	}
	const ratio = natural.value && natural.value.w / natural.value.h;
	if (!ratio) return null;
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
	if (props.disabled) return;
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
	if (zoom.value > 1) emitViewBoxAt(zoom.value, x, y);
}

// --- zoom crop (objectViewBox inset window centred on the focus point) -----

const insets = computed(() => {
	const m = (props.viewBox || "").match(/inset\(\s*([\d.]+)%\s+([\d.]+)%\s+([\d.]+)%\s+([\d.]+)%\s*\)/);
	if (!m) return null;
	const [top, right, bottom, left] = m.slice(1).map(Number);
	return { top, right, bottom, left };
});

const zoom = computed(() => {
	if (!insets.value) return 1;
	const span = 100 - insets.value.left - insets.value.right;
	return span > 0 ? Math.round((100 / span) * 20) / 20 : 1;
});

function stepZoom(dir: number) {
	const z = Math.min(4, Math.max(1, Math.round((zoom.value + dir * 0.25) * 20) / 20));
	emitViewBoxAt(z, point.value.x, point.value.y);
}

function emitViewBoxAt(z: number, fx: number, fy: number) {
	if (props.viewBox === undefined) return;
	if (z <= 1.001) {
		emit("update:viewBox", "");
		return;
	}
	const span = 100 / z;
	const left = (fx / 100) * (100 - span);
	const top = (fy / 100) * (100 - span);
	const f = (n: number) => Math.round(n * 10) / 10;
	emit("update:viewBox", `inset(${f(top)}% ${f(100 - span - left)}% ${f(100 - span - top)}% ${f(left)}%)`);
}

// The white frame: the part of the image the element ACTUALLY shows — the zoom
// window narrowed by the cover fit against the element's own aspect ratio, so
// dragging the dot slides the frame exactly as the crop slides on canvas.
const cropRectStyle = computed(() => {
	const rect = imageRect.value;
	if (!rect || !natural.value || !(insets.value || props.targetRatio)) return null;
	const winX = (insets.value?.left ?? 0) / 100;
	const winY = (insets.value?.top ?? 0) / 100;
	const spanX = insets.value ? (100 - insets.value.left - insets.value.right) / 100 : 1;
	const spanY = insets.value ? (100 - insets.value.top - insets.value.bottom) / 100 : 1;
	let x = winX;
	let y = winY;
	let w = spanX;
	let h = spanY;
	if (props.targetRatio) {
		const contentRatio = (natural.value.w * spanX) / (natural.value.h * spanY);
		if (contentRatio > props.targetRatio) {
			const frac = props.targetRatio / contentRatio;
			x = winX + (point.value.x / 100) * spanX * (1 - frac);
			w = spanX * frac;
		} else if (contentRatio < props.targetRatio) {
			const frac = contentRatio / props.targetRatio;
			y = winY + (point.value.y / 100) * spanY * (1 - frac);
			h = spanY * frac;
		}
	}
	return {
		left: `${rect.x + x * rect.w}px`,
		top: `${rect.y + y * rect.h}px`,
		width: `${w * rect.w}px`,
		height: `${h * rect.h}px`,
	};
});
</script>
