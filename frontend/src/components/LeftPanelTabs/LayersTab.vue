<template>
	<div class="min-h-full p-3 pr-0" @click.stop="canvasStore.activeCanvas?.clearSelection()">
		<span class="flex items-center gap-2 pb-2 text-sm capitalize text-ink-gray-4">
			<span
				:class="[
					canvasStore.activeCanvas?.canvasProps.breakpoints.find(
						(b) => b.device === canvasStore.activeCanvas?.activeBreakpoint,
					)?.icon || 'lucide-monitor',
					'size-3',
				]"
				aria-hidden="true" />
			{{ canvasStore.activeCanvas?.activeBreakpoint }}
		</span>
		<BlockLayers
			class="block-layers w-fit min-w-full pr-3"
			v-if="pageCanvas"
			:disable-draggable="true"
			:readonly="builderStore.readOnlyMode"
			ref="pageLayers"
			:blocks="[pageCanvas?.getRootBlock() as Block]"
			v-show="canvasStore.editingMode == 'page'" />
		<BlockLayers
			class="block-layers w-fit min-w-full pr-3"
			ref="componentLayers"
			:disable-draggable="true"
			:readonly="builderStore.readOnlyMode"
			:blocks="[fragmentCanvas?.getRootBlock()]"
			:indent="5"
			:adjustForRoot="false"
			v-if="canvasStore.editingMode === 'fragment' && fragmentCanvas" />
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import BlockLayers from "@/components/BlockLayers.vue";
import BuilderCanvas from "@/components/BuilderCanvas.vue";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import { inject, nextTick, Ref, ref, watch, watchEffect } from "vue";

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();

const pageLayers = ref<InstanceType<typeof BlockLayers> | null>(null);
const componentLayers = ref<InstanceType<typeof BlockLayers> | null>(null);

const pageCanvas = inject("pageCanvas") as Ref<InstanceType<typeof BuilderCanvas> | null>;
const fragmentCanvas = inject("fragmentCanvas") as Ref<InstanceType<typeof BuilderCanvas> | null>;

watchEffect(() => {
	if (pageLayers.value) {
		builderStore.activeLayers = pageLayers.value;
	} else if (componentLayers.value) {
		builderStore.activeLayers = componentLayers.value;
	}
});

// moved out of BlockLayers for performance
// TODO: Find a better way to do this
watch(
	() => canvasStore.activeCanvas?.hoveredBlock,
	() => {
		document.querySelectorAll(`[data-block-layer-id].hovered-block`).forEach((el) => {
			el.classList.remove("hovered-block");
		});
		if (canvasStore.activeCanvas?.hoveredBlock) {
			document
				.querySelector(`[data-block-layer-id="${canvasStore.activeCanvas.hoveredBlock}"]`)
				?.classList.add("hovered-block");
		}
	},
);

watch(
	() => canvasStore.activeCanvas?.selectedBlockIds,
	async () => {
		await nextTick();
		const selectedBlocks = document.querySelectorAll(`[data-block-layer-id].block-selected`);
		selectedBlocks.forEach((el) => el.classList.remove("block-selected"));
		Array.from(canvasStore.activeCanvas?.selectedBlockIds || new Set([])).forEach((blockId: string) => {
			const blockElement = document.querySelector(`[data-block-layer-id="${blockId}"]`);
			blockElement?.classList.add("block-selected");
		});
	},
	{ deep: true },
);
</script>
