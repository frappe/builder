<template>
	<div v-if="target.active" ref="rootEl" class="pointer-events-none fixed inset-0 z-[250]" :style="clipStyle">
		<!-- container outline: only when moving into a DIFFERENT container, so a
		     plain in-place reorder stays quiet (no flicker) -->
		<div
			v-if="target.containerRect && !target.isSameContainer"
			class="drop-container-highlight absolute rounded-[4px]"
			:class="accentClass"
			:style="containerStyle" />

		<!-- insertion line — layout-aware (flex row/column, wrapped flex, grid) -->
		<div
			v-if="target.line"
			class="drop-line absolute rounded-full"
			:class="[accentClass, `is-${target.line.orientation}`]"
			:style="lineStyle">
			<span class="drop-line-cap drop-line-cap--start" />
			<span class="drop-line-cap drop-line-cap--end" />
		</div>
	</div>
</template>

<script setup lang="ts">
import useCanvasStore from "@/stores/canvasStore";
import { computed, ref } from "vue";

const canvasStore = useCanvasStore();
const target = computed(() => canvasStore.reorderTarget);

const rootEl = ref<HTMLElement>();

// Clip the (full-viewport) overlay to the canvas region so indicators never
// paint over the side panels. Recomputes each drag update (target changes) —
// getBoundingClientRect is a cheap read and the panels don't move mid-drag.
const clipStyle = computed(() => {
	if (!target.value.active) return {};
	const host = rootEl.value?.closest("[data-builder-canvas]") as HTMLElement | null;
	if (!host) return {};
	const r = host.getBoundingClientRect();
	const top = Math.max(0, r.top);
	const left = Math.max(0, r.left);
	const right = Math.max(0, window.innerWidth - r.right);
	const bottom = Math.max(0, window.innerHeight - r.bottom);
	return { clipPath: `inset(${top}px ${right}px ${bottom}px ${left}px)` };
});

const accentClass = computed(() => (target.value.isComponentParent ? "accent-purple" : "accent-blue"));

const containerStyle = computed(() => {
	const r = target.value.containerRect;
	return r ? { left: `${r.left}px`, top: `${r.top}px`, width: `${r.width}px`, height: `${r.height}px` } : {};
});

const LINE = 3;
const lineStyle = computed(() => {
	const l = target.value.line;
	if (!l) return { display: "none" };
	if (l.orientation === "vertical") {
		return { left: `${l.left - LINE / 2}px`, top: `${l.top}px`, width: `${LINE}px`, height: `${l.length}px` };
	}
	return { left: `${l.left}px`, top: `${l.top - LINE / 2}px`, width: `${l.length}px`, height: `${LINE}px` };
});
</script>

<style scoped>
.drop-line.accent-blue {
	background-color: theme("colors.blue.500");
}
.drop-line.accent-purple {
	background-color: theme("colors.purple.500");
}
.drop-line-cap {
	position: absolute;
	width: 7px;
	height: 7px;
	border-radius: 9999px;
	background: inherit;
}
.drop-line.is-vertical .drop-line-cap--start {
	left: 50%;
	top: 0;
	transform: translate(-50%, -50%);
}
.drop-line.is-vertical .drop-line-cap--end {
	left: 50%;
	top: 100%;
	transform: translate(-50%, -50%);
}
.drop-line.is-horizontal .drop-line-cap--start {
	top: 50%;
	left: 0;
	transform: translate(-50%, -50%);
}
.drop-line.is-horizontal .drop-line-cap--end {
	top: 50%;
	left: 100%;
	transform: translate(-50%, -50%);
}

.drop-container-highlight.accent-blue {
	box-shadow: inset 0 0 0 1.5px theme("colors.blue.400 / 70%");
	background-color: theme("colors.blue.400 / 6%");
}
.drop-container-highlight.accent-purple {
	box-shadow: inset 0 0 0 1.5px theme("colors.purple.400 / 70%");
	background-color: theme("colors.purple.400 / 6%");
}
</style>
