<template>
	<div class="flex-col bg-gray-100">
		<BuilderToolbar class="relative z-30"></BuilderToolbar>
		<div>
			<BuilderSidebar
				class="fixed left-0 top-[3.5rem] bottom-0 z-20 hidden w-1/6 overflow-auto border-r-2 border-gray-100 bg-white p-5 lg:block">
			</BuilderSidebar>
			<BuilderCanvas
				class="canvas-container absolute left-0 right-0 top-[3.5rem] bottom-0 flex justify-center overflow-hidden bg-gray-100 p-10">
			</BuilderCanvas>
			<BlockProperties
				class="fixed right-0 top-[3.5rem] bottom-0 z-20 w-1/5 overflow-auto border-l-2 border-gray-100 bg-white p-5 pr-2">
			</BlockProperties>
		</div>
	</div>
</template>

<script setup>
import BuilderCanvas from "../components/BuilderCanvas.vue";
import BuilderToolbar from "../components/BuilderToolbar.vue";
import BuilderSidebar from "../components/BuilderSidebar.vue";
import BlockProperties from "../components/BlockProperties.vue";
</script>
