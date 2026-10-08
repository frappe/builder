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
		const svg = await loadRuntimeLucideIcon(name);
		// a slow download for an old name must not replace the icon of the new name
		if (name === props.name) iconSvg.value = svg;
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
