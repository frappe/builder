<template>
	<div class="flex-col bg-gray-100 page-builder">
		<BuilderToolbar class="relative z-30 dark:bg-zinc-900 dark:border-b-[1px] dark:border-gray-800"></BuilderToolbar>
		<div>
			<BuilderSidebar
				class="fixed left-0 top-[var(--toolbar-height)] bottom-0 z-20 overflow-auto border-r-[1px] bg-white p-4 dark:bg-zinc-900 dark:border-gray-800 no-scrollbar">
			</BuilderSidebar>
			<BuilderCanvas
				class="canvas-container absolute top-[var(--toolbar-height)] bottom-0 flex justify-center overflow-hidden bg-gray-200 p-10 dark:bg-zinc-800">
			</BuilderCanvas>
			<BlockPropertiesEditor
				class="fixed right-0 top-[var(--toolbar-height)] bottom-0 z-20 overflow-auto border-l-[1px] bg-white p-4 pr-2 dark:bg-zinc-900 dark:border-gray-800 no-scrollbar">
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