<template>
	<div
		:style="{
			width: `${store.builderLayout.rightPanelWidth}px`,
		}">
		<div class="relative min-h-full">
			<PanelResizer
				:dimension="store.builderLayout.rightPanelWidth"
				side="left"
				@resize="(width) => (store.builderLayout.rightPanelWidth = width)"
				:min-dimension="275"
				:max-dimension="400" />
			<BlockProperties class="p-3" />
		</div>
	</div>
</template>
<script setup lang="ts">
import useStore from "@/store";
import BlockProperties from "./BlockProperties.vue";
import PanelResizer from "./PanelResizer.vue";
const store = useStore();
</script>
