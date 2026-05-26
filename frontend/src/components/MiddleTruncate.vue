<template>
	<component
		:is="as"
		ref="wrapper"
		class="flex w-full overflow-hidden whitespace-nowrap"
		:title="text"
		:style="hasOverflow ? 'mask-image: linear-gradient(to right, black 90%, transparent)' : ''">
		<span class="min-w-8 truncate">{{ leading }}</span>
		<span v-if="trailing">{{ trailing }}</span>
	</component>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, useTemplateRef } from "vue";

const props = defineProps<{ text: string; as?: string }>();
const as = computed(() => props.as ?? "div");

const wrapper = useTemplateRef<HTMLElement>("wrapper");
const hasOverflow = ref(false);

let observer: ResizeObserver;

onMounted(() => {
	const check = () => {
		hasOverflow.value = (wrapper.value?.scrollWidth ?? 0) > (wrapper.value?.clientWidth ?? 0);
	};
	observer = new ResizeObserver(check);
	observer.observe(wrapper.value!);
	check();
});

onUnmounted(() => observer?.disconnect());

const suffixLen = computed(() => {
	const len = props.text.length;
	return len < 10 ? 0 : Math.floor(len * 0.35);
});

const leading = computed(() => (suffixLen.value ? props.text.slice(0, -suffixLen.value) : props.text));
const trailing = computed(() => (suffixLen.value ? props.text.slice(-suffixLen.value) : ""));
</script>
