<template>
	<component
		:is="as"
		ref="wrapper"
		class="flex w-full overflow-hidden whitespace-nowrap"
		:title="text"
		:style="maskStyle"
		@mouseenter="marquee && startScroll()"
		@mouseleave="marquee && stopScroll()">
		<span v-if="marquee" ref="scroller" class="marquee-text flex-none" :style="scrollerStyle">{{ text }}</span>
		<template v-else>
			<span class="min-w-8 truncate">{{ leading }}</span>
			<span v-if="trailing">{{ trailing }}</span>
		</template>
	</component>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, useTemplateRef } from "vue";

const props = defineProps<{
	text: string;
	as?: string;
	marquee?: boolean;
}>();
const as = computed(() => props.as ?? "div");
const SCROLL_SPEED = 60;
const START_DELAY = 0.3;
const RESET_DURATION = 0.2;

const wrapper = useTemplateRef<HTMLElement>("wrapper");
const scroller = useTemplateRef<HTMLElement>("scroller");
const hasOverflow = ref(false);
const scrollDistance = ref(0);

let observer: ResizeObserver;

onMounted(() => {
	const check = () => {
		hasOverflow.value = (wrapper.value?.scrollWidth ?? 0) > (wrapper.value?.clientWidth ?? 0);
	};
	observer = new ResizeObserver(check);
	observer.observe(wrapper.value!);
	if (scroller.value) observer.observe(scroller.value);
	check();
});

onUnmounted(() => observer?.disconnect());

// measured on hover rather than kept live
const startScroll = () => {
	const overflow = (wrapper.value?.scrollWidth ?? 0) - (wrapper.value?.clientWidth ?? 0);
	scrollDistance.value = Math.max(Math.ceil(overflow), 0);
};

const stopScroll = () => (scrollDistance.value = 0);

const scrollerStyle = computed(() => {
	const scrolling = scrollDistance.value > 0;
	return {
		transform: `translateX(-${scrollDistance.value}px)`,
		transitionDuration: `${scrolling ? scrollDistance.value / SCROLL_SPEED : RESET_DURATION}s`,
		transitionDelay: `${scrolling ? START_DELAY : 0}s`,
	};
});

const maskStyle = computed(() =>
	hasOverflow.value && !scrollDistance.value
		? "mask-image: linear-gradient(to right, black 90%, transparent)"
		: "",
);

const suffixLen = computed(() => {
	const len = props.text.length;
	return len < 10 ? 0 : Math.floor(len * 0.35);
});

const leading = computed(() => (suffixLen.value ? props.text.slice(0, -suffixLen.value) : props.text));
const trailing = computed(() => (suffixLen.value ? props.text.slice(-suffixLen.value) : ""));
</script>

<style scoped>
.marquee-text {
	transition-property: transform;
	transition-timing-function: linear;
}

@media (prefers-reduced-motion: reduce) {
	.marquee-text {
		transition-duration: 0s !important;
		transition-delay: 0s !important;
	}
}
</style>