<template>
	<component
		:is="as"
		ref="wrapper"
		class="flex w-full overflow-hidden whitespace-nowrap"
		:class="{ 'marquee-clip': marquee }"
		:title="text"
		:style="wrapperStyle">
		<span v-if="marquee" ref="scroller" class="marquee-text flex-none">{{ text }}</span>
		<template v-else>
			<span class="min-w-8 truncate">{{ leading }}</span>
			<span v-if="trailing">{{ trailing }}</span>
		</template>
	</component>
</template>

<script setup lang="ts">
import type { CSSProperties } from "vue";
import { computed, onMounted, onUnmounted, ref, useTemplateRef } from "vue";

const props = defineProps<{
	text: string;
	as?: string;
	marquee?: boolean;
}>();
const as = computed(() => props.as ?? "div");

const MASK = "linear-gradient(to right, black 90%, transparent)";
// px per second, so long and short names read at the same pace
const SCROLL_SPEED = 60;

const wrapper = useTemplateRef<HTMLElement>("wrapper");
const scroller = useTemplateRef<HTMLElement>("scroller");
const hasOverflow = ref(false);
const scrollDistance = ref(0);

let observer: ResizeObserver;

onMounted(() => {
	const check = () => {
		const overflow = (wrapper.value?.scrollWidth ?? 0) - (wrapper.value?.clientWidth ?? 0);
		hasOverflow.value = overflow > 0;
		scrollDistance.value = Math.max(Math.ceil(overflow), 0);
	};
	observer = new ResizeObserver(check);
	observer.observe(wrapper.value!);
	// the text can outgrow the box without the box resizing, e.g. a font preview loading in
	if (scroller.value) observer.observe(scroller.value);
	check();
});

onUnmounted(() => observer?.disconnect());

// measured here, applied by CSS: the reveal keys off a `data-highlighted` attribute, and only
// CSS can react to one without the row re-rendering
const wrapperStyle = computed<CSSProperties>(() => {
	if (!props.marquee) return { maskImage: hasOverflow.value ? MASK : undefined };
	return {
		"--marquee-mask": hasOverflow.value ? MASK : "none",
		"--marquee-distance": `${scrollDistance.value}px`,
		"--marquee-duration": `${scrollDistance.value / SCROLL_SPEED}s`,
	};
});

const suffixLen = computed(() => {
	const len = props.text.length;
	return len < 10 ? 0 : Math.floor(len * 0.35);
});

const leading = computed(() => (suffixLen.value ? props.text.slice(0, -suffixLen.value) : props.text));
const trailing = computed(() => (suffixLen.value ? props.text.slice(-suffixLen.value) : ""));
</script>

<style scoped>
.marquee-clip {
	mask-image: var(--marquee-mask, none);
}

.marquee-text {
	transform: translateX(0);
	/* the way back */
	transition: transform 0.2s linear 0s;
}

/* a pointer and the arrow keys set the same attribute, so one rule covers both */
.marquee-clip:hover,
[data-highlighted] .marquee-clip {
	mask-image: none;
}

.marquee-clip:hover .marquee-text,
[data-highlighted] .marquee-text {
	transform: translateX(calc(-1 * var(--marquee-distance, 0px)));
	transition-duration: var(--marquee-duration, 0s);
	/* so a row brushed past on the way to another doesn't set off */
	transition-delay: 0.3s;
}

/* jump to the end rather than travel, so the tail stays reachable */
@media (prefers-reduced-motion: reduce) {
	.marquee-text {
		transition-duration: 0s !important;
		transition-delay: 0s !important;
	}
}
</style>
