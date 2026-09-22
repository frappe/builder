<template>
	<div>
		<div
			v-for="(_, index) in itemCount"
			:key="index"
			:data-block-layer-id="index === activeIndex ? child.blockId : undefined"
			:data-indent="indent"
			class="block-layer-item relative min-w-24 cursor-pointer select-none rounded border border-transparent bg-surface-base bg-opacity-50 text-base text-ink-gray-7"
			:class="{ 'block-selected': index === activeIndex && isChildSelected }"
			@click.stop="showItem(index, $event)"
			@mouseover.stop="!canvasStore.isDragging && canvasStore.activeCanvas?.setHoveredBlock(child.blockId)"
			@mouseleave.stop="!canvasStore.isDragging && canvasStore.activeCanvas?.setHoveredBlock(null)">
			<span
				class="group my-[7px] flex items-center gap-1.5 pr-[2px] font-medium"
				:style="{ paddingLeft: `${indent}px` }"
				:class="{ '!opacity-50': !child.isVisible() || isParentHidden }">
				<div>
					<div class="scroll-into-view-anchor absolute ml-20"></div>
				</div>
				<span :class="[child.getIcon(), 'h-3 w-3']" aria-hidden="true" />
				<span class="min-w-[2em] max-w-64 truncate">{{ child.getBlockDescription() }} {{ index + 1 }}</span>
			</span>
			<BlockLayers
				v-if="index === activeIndex && child.hasChildren()"
				:blocks="child.children"
				:indent="indent + 24"
				:readonly="readonly"
				:is-parent-hidden="isParentHidden || !child.isVisible()" />
		</div>
	</div>
</template>

<script setup lang="ts">
import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import { computed } from "vue";
import BlockLayers from "./BlockLayers.vue";

// DataLoaderBlock renders at most this many items
const MAX_ITEMS = 100;

const props = withDefaults(
	defineProps<{
		repeater: Block;
		indent?: number;
		isParentHidden?: boolean;
		readonly?: boolean;
	}>(),
	{
		indent: 0,
		isParentHidden: false,
		readonly: false,
	},
);

const canvasStore = useCanvasStore();

const child = computed(() => props.repeater.children[0]);

const itemCount = computed(() => Math.min(Math.max(props.repeater.getRepeaterPropItems().length, 1), MAX_ITEMS));

const activeIndex = computed(() =>
	Math.min(canvasStore.repeaterPreviewIndex[props.repeater.blockId] ?? 0, itemCount.value - 1),
);

const isChildSelected = computed(() => Boolean(canvasStore.activeCanvas?.selectedBlockIds.has(child.value.blockId)));

const showItem = (index: number, event: MouseEvent) => {
	canvasStore.repeaterPreviewIndex[props.repeater.blockId] = index;
	// picking an item already scrolls it into view inside the repeater; panning the canvas too would
	// measure the item while it is still being swapped in and move the canvas off to one side
	canvasStore.selectBlock(child.value, event, false, false);
};
</script>
