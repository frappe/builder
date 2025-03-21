<template>
	<div
		:style="{
			width: `${builderStore.builderLayout.rightPanelWidth}px`,
		}">
		<div class="relative min-h-full">
			<PanelResizer
				:dimension="builderStore.builderLayout.rightPanelWidth"
				side="left"
				@resize="(width) => (builderStore.builderLayout.rightPanelWidth = width)"
				:min-dimension="275"
				:max-dimension="400" />
			<BlockProperties class="p-3" />
		</div>
	</div>
</template>
<script setup lang="ts">
import useBuilderStore from "@/stores/builderStore";
import BlockProperties from "./BlockProperties.vue";
import PanelResizer from "./PanelResizer.vue";
const builderStore = useBuilderStore();
</script>
