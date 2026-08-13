<template>
	<div class="flex gap-2">
		<Button
			v-for="mode in modes"
			:key="mode.mode"
			:variant="builderStore.mode === mode.mode ? 'subtle' : 'ghost'"
			:tooltip="mode.description"
			:icon="mode.icon"
			@click="() => (builderStore.mode = mode.mode as BuilderMode)"
			:active="builderStore.mode === mode.mode"></Button>
	</div>
</template>
<script setup lang="ts">
import useBuilderStore from "@/stores/builderStore";
import { __ } from "@/translation";

const builderStore = useBuilderStore();

// one item, not four: they are a tight visual group
const modes = [
	{ mode: "select", icon: "lucide-mouse-pointer", description: __("Select (v)") },
	{ mode: "container", icon: "lucide-square", description: __("Container (c)") },
	{ mode: "text", icon: "lucide-type", description: __("Text (t)") },
	{ mode: "image", icon: "lucide-image", description: __("Image (i)") },
];
</script>
