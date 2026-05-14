<template>
	<component
		:is="as"
		ref="wrapper"
		class="flex w-full overflow-hidden whitespace-nowrap"
		:title="text"
		:style="applyGradient">
		<span class="min-w-8 truncate">{{ truncatedSplit }}</span>
		<span v-if="textParts.length > 1">{{ endSplit }}</span>
	</component>
</template>

<script setup lang="ts">
import { computed, useTemplateRef, ref, watchEffect } from "vue";

const wrapperRef: any = useTemplateRef("wrapper");
const hasOverflow = ref(false);

const props = withDefaults(
	defineProps<{
		text: string;
		as?: string;
	}>(),
	{
		as: "div",
	},
);

watchEffect(() => {
	if (!wrapperRef.value) return;

	const checkOverflow = () => {
		hasOverflow.value = wrapperRef.value!.scrollWidth > wrapperRef.value!.clientWidth;
	};

	checkOverflow();

	const resizeObserver = new ResizeObserver(checkOverflow);
	resizeObserver.observe(wrapperRef.value);

	return () => resizeObserver.disconnect();
});

const textParts = computed(() => {
	return props.text.split(".");
});

const truncatedSplit = computed(() => {
	return textParts.value.slice(0, textParts.value.length - 1).join(".");
});

const endSplit = computed(() => {
	return `.${textParts.value[textParts.value.length - 1]}`;
});

const applyGradient = computed(() => {
	return hasOverflow.value ? "mask-image: linear-gradient(to right, black 90%, transparent)" : "";
});
</script>
