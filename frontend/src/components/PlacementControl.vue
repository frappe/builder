<template>
	<div class="items-top relative flex justify-center">
		<div class="relative h-fit w-fit">
			<div class="group grid grid-cols-3 rounded-sm bg-surface-gray-2 p-1.5">
				<div
					v-for="option in placementOptions"
					:key="option"
					class="group/option flex h-5 w-5 cursor-pointer items-center justify-center opacity-50"
					:class="{
						'!justify-start': option.includes('left'),
						'!justify-end': option.includes('right'),
						'!items-start': option.includes('top'),
						'!items-end': option.includes('bottom'),
					}"
					@mouseenter="hoveredSlot = getSlot(option)"
					@mouseleave="hoveredSlot = null"
					@click="setAlignment(option)"
					@dblclick="setAlignment(option, true)">
					<div
						class="flex size-1 items-center justify-center rounded-full bg-surface-gray-5 opacity-50"
						:class="{ 'group-hover/option:hidden': !isDistributed }"></div>
					<div
						v-if="!isDistributed"
						class="hidden w-5 gap-[2px] hover:opacity-100 group-hover/option:flex"
						:style="previewStyle(option)">
						<div
							class="rounded-sm bg-surface-gray-5"
							:class="{
								'h-2 w-1': direction === 'row',
								'h-1 w-2': direction === 'column',
							}"></div>
						<div
							class="rounded-sm bg-surface-gray-5"
							:class="{
								'h-3 w-1': direction === 'row',
								'h-1 w-3': direction === 'column',
							}"></div>
						<div
							class="rounded-sm bg-surface-gray-5"
							:class="{
								'h-2 w-1': direction === 'row',
								'h-1 w-2': direction === 'column',
							}"></div>
					</div>
				</div>
			</div>
			<div
				class="pointer-events-none absolute top-0 flex h-full w-full cursor-pointer gap-[2px] rounded-sm p-1.5"
				:style="selectedOverlayStyle">
				<div
					class="rounded-sm bg-surface-gray-6"
					:class="{
						'h-1 w-2': direction === 'column',
						'h-2 w-1': direction === 'row',
					}"></div>
				<div
					class="rounded-sm bg-surface-gray-6"
					:class="{
						'h-1 w-3': direction === 'column',
						'h-3 w-1': direction === 'row',
					}"></div>
				<div
					class="rounded-sm bg-surface-gray-6"
					:class="{
						'h-1 w-2': direction === 'column',
						'h-2 w-1': direction === 'row',
					}"></div>
			</div>
			<div
				v-if="isDistributed && hoveredSlot"
				class="pointer-events-none absolute top-0 flex h-full w-full cursor-pointer gap-[2px] rounded-sm p-1.5 opacity-40"
				:style="hoverOverlayStyle">
				<div
					class="rounded-sm bg-surface-gray-5"
					:class="{
						'h-1 w-2': direction === 'column',
						'h-2 w-1': direction === 'row',
					}"></div>
				<div
					class="rounded-sm bg-surface-gray-5"
					:class="{
						'h-1 w-3': direction === 'column',
						'h-3 w-1': direction === 'row',
					}"></div>
				<div
					class="rounded-sm bg-surface-gray-5"
					:class="{
						'h-1 w-2': direction === 'column',
						'h-2 w-1': direction === 'row',
					}"></div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import blockController from "@/utils/blockController";
import { type CSSProperties, computed, ref } from "vue";

const placementOptions = [
	"top-left",
	"top-middle",
	"top-right",
	"middle-left",
	"middle-middle",
	"middle-right",
	"bottom-left",
	"bottom-middle",
	"bottom-right",
];

const direction = computed(() => (blockController.getStyle("flexDirection") || "row") as string);
const justifyContent = computed(() => (blockController.getStyle("justifyContent") || "flex-start") as string);
const alignItems = computed(() => (blockController.getStyle("alignItems") || "stretch") as string);

const toFlex = (s: string) =>
	s === "top" || s === "left" ? "flex-start" : s === "middle" ? "center" : "flex-end";

const isDistributed = computed(() => isSpacing(justifyContent.value));
const hoveredSlot = ref<string | null>(null);

const getSlot = (option: string) => {
	const [vertical, horizontal] = option.split("-");
	return direction.value === "row" ? vertical : horizontal;
};

const hoverAlignItems = computed(() =>
	isDistributed.value && hoveredSlot.value ? toFlex(hoveredSlot.value) : alignItems.value,
);

const selectedOverlayStyle = computed<CSSProperties>(() => ({
	flexDirection: direction.value as CSSProperties["flexDirection"],
	justifyContent: justifyContent.value as CSSProperties["justifyContent"],
	alignItems: alignItems.value,
}));

const hoverOverlayStyle = computed<CSSProperties>(() => ({
	flexDirection: direction.value as CSSProperties["flexDirection"],
	justifyContent: justifyContent.value as CSSProperties["justifyContent"],
	alignItems: hoverAlignItems.value,
}));

const previewStyle = (option: string): CSSProperties => {
	const [vertical, horizontal] = option.split("-");
	const isRow = direction.value === "row";
	const wouldBeJC = isSpacing(justifyContent.value)
		? justifyContent.value
		: toFlex(isRow ? horizontal : vertical);
	return {
		flexDirection: direction.value as CSSProperties["flexDirection"],
		justifyContent: wouldBeJC as CSSProperties["justifyContent"],
		alignItems: toFlex(isRow ? vertical : horizontal),
	};
};

const isSpacing = (v: string) => v.startsWith("space-");

const setAlignment = (alignment: string, spaceBetween: boolean = false) => {
	const [vertical, horizontal] = alignment.split("-");
	const isRow = direction.value === "row";
	blockController.setStyle("alignItems", toFlex(isRow ? vertical : horizontal));
	if (spaceBetween) {
		blockController.setStyle(
			"justifyContent",
			isSpacing(justifyContent.value) ? toFlex(isRow ? horizontal : vertical) : "space-between",
		);
	} else if (!isSpacing(justifyContent.value)) {
		blockController.setStyle("justifyContent", toFlex(isRow ? horizontal : vertical));
	}
};
</script>
