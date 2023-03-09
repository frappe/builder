<template>
	<div class="flex-col bg-gray-100 page-builder">
		<BuilderToolbar class="relative z-30 dark:bg-gray-900"></BuilderToolbar>
		<div>
			<BuilderSidebar
				class="fixed left-0 top-[var(--toolbar-height)] bottom-0 z-20 w-[var(--left-panel-width)] overflow-auto border-r-2 border-gray-100 bg-white p-5 dark:bg-gray-900 dark:border-gray-800">
			</BuilderSidebar>
			<BuilderCanvas
				class="canvas-container absolute left-[var(--left-panel-width)] right-[var(--right-panel-width)] top-[var(--toolbar-height)] bottom-0 flex justify-center overflow-hidden bg-gray-100 p-10 dark:bg-gray-800">
			</BuilderCanvas>
			<BlockPropertiesEditor
				class="fixed right-0 top-[var(--toolbar-height)] bottom-0 z-20 w-[var(--right-panel-width)] overflow-auto border-l-2 border-gray-100 bg-white p-5 pr-2 dark:bg-gray-900 dark:border-gray-800">
			</BlockPropertiesEditor>
		</div>
	</div>
</template>

<script setup>
import BuilderCanvas from "../components/BuilderCanvas.vue";
import BuilderToolbar from "../components/BuilderToolbar.vue";
import BuilderSidebar from "../components/BuilderSidebar.vue";
import BlockPropertiesEditor from "../components/BlockPropertiesEditor.vue";
</script>

<style>
.page-builder {
	--left-panel-width: 17rem;
	--right-panel-width: 20rem;
	--toolbar-height: 3.5rem;
}
</style>