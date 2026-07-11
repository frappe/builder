<template>
	<div v-if="target.active" class="pointer-events-none fixed inset-0 z-[250]">
		<!-- container highlight: shows which layout you're dropping into -->
		<div
			v-if="target.containerRect"
			class="drop-container-highlight absolute rounded-[4px]"
			:class="accentClass"
			:style="containerStyle" />

		<!-- SAME-container: exact in-flow slot box (measured from the placeholder) -->
		<div
			v-if="target.mode === 'slot' && target.slotRect"
			class="drop-slot absolute rounded-[4px]"
			:class="accentClass"
			:style="slotStyle" />

		<!-- CROSS-container: no-reflow line between the target's children -->
		<div
			v-if="target.mode === 'line' && target.line"
			class="drop-line absolute rounded-full"
			:class="[accentClass, `is-${target.line.orientation}`]"
			:style="lineStyle">
			<span class="drop-line-cap drop-line-cap--start" />
			<span class="drop-line-cap drop-line-cap--end" />
		</div>

		<!-- spacing guide: the container's gap -->
		<div v-if="target.spacing" class="drop-spacing-pill absolute" :class="accentClass" :style="pillStyle">
			{{ target.spacing.value }}
		</div>
	</div>
</template>

<script setup lang="ts">
import useCanvasStore from "@/stores/canvasStore";
import { computed } from "vue";

const canvasStore = useCanvasStore();
const target = computed(() => canvasStore.reorderTarget);

const accentClass = computed(() => (target.value.isComponentParent ? "accent-purple" : "accent-blue"));

const rectStyle = (r: { top: number; left: number; width: number; height: number } | null) =>
	r ? { left: `${r.left}px`, top: `${r.top}px`, width: `${r.width}px`, height: `${r.height}px` } : {};

const containerStyle = computed(() => rectStyle(target.value.containerRect));
const slotStyle = computed(() => rectStyle(target.value.slotRect));

const LINE = 3;
const lineStyle = computed(() => {
	const l = target.value.line;
	if (!l) return { display: "none" };
	if (l.orientation === "vertical") {
		return { left: `${l.left - LINE / 2}px`, top: `${l.top}px`, width: `${LINE}px`, height: `${l.length}px` };
	}
	return { left: `${l.left}px`, top: `${l.top - LINE / 2}px`, width: `${l.length}px`, height: `${LINE}px` };
});

const pillStyle = computed(() => {
	const s = target.value.spacing;
	if (!s) return { display: "none" };
	return { left: `${s.left}px`, top: `${s.top}px` };
});
</script>

<style scoped>
.drop-slot.accent-blue {
	box-shadow: inset 0 0 0 2px theme("colors.blue.500");
	background-color: theme("colors.blue.500 / 12%");
}
.drop-slot.accent-purple {
	box-shadow: inset 0 0 0 2px theme("colors.purple.500");
	background-color: theme("colors.purple.500 / 12%");
}

.drop-line.accent-blue {
	background-color: theme("colors.blue.500");
	box-shadow:
		0 0 0 1px theme("colors.blue.500 / 25%"),
		0 0 6px theme("colors.blue.500 / 55%");
}
.drop-line.accent-purple {
	background-color: theme("colors.purple.500");
	box-shadow:
		0 0 0 1px theme("colors.purple.500 / 25%"),
		0 0 6px theme("colors.purple.500 / 55%");
}
.drop-line-cap {
	position: absolute;
	width: 7px;
	height: 7px;
	border-radius: 9999px;
	background: inherit;
	box-shadow: inherit;
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

.drop-spacing-pill {
	transform: translate(-50%, -140%);
	padding: 1px 6px;
	border-radius: 9999px;
	font-size: 10px;
	line-height: 15px;
	font-weight: 600;
	color: #fff;
	white-space: nowrap;
}
.drop-spacing-pill.accent-blue {
	background-color: theme("colors.blue.500");
}
.drop-spacing-pill.accent-purple {
	background-color: theme("colors.purple.500");
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
