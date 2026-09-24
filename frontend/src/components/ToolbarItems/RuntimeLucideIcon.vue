<template>
	<span class="block h-[1em] w-[1em] shrink-0" :style="maskStyle" aria-hidden="true" />
</template>

<script setup lang="ts">
import { createLucideMaskImage, loadRuntimeLucideIcon } from "@/runtimeLucideIcons";
import { computed, ref, watch } from "vue";

const props = defineProps<{ name: string }>();
const iconSvg = ref<string>();

watch(
	() => props.name,
	async (name) => {
		iconSvg.value = await loadRuntimeLucideIcon(name);
	},
	{ immediate: true },
);

const maskStyle = computed(() => {
	if (!iconSvg.value) return;

	const maskImage = createLucideMaskImage(iconSvg.value);
	return {
		backgroundColor: "currentColor",
		WebkitMaskImage: maskImage,
		maskImage,
		WebkitMaskRepeat: "no-repeat",
		maskRepeat: "no-repeat",
		WebkitMaskPosition: "center",
		maskPosition: "center",
		WebkitMaskSize: "contain",
		maskSize: "contain",
	};
});
</script>
