<template>
	<div class="flex">
		<PanelResizer
			:dimension="builderStore.builderLayout.leftPanelWidth"
			side="right"
			:minDimension="200	"
			:maxDimension="500"
			@resize="(width) => (builderStore.builderLayout.leftPanelWidth = width)" />
		<div
			class="flex min-h-full flex-col items-center gap-3 border-r border-outline-gray-1 p-3"
			ref="miniSidebar">
			<Tooltip v-for="option of leftPanelOptions" :key="option.value" :text="option.label" placement="right">
				<button
					class="flex size-8 items-center justify-center rounded text-ink-gray-7 hover:bg-surface-gray-2 focus:!bg-surface-gray-3"
					:class="{
						'bg-surface-gray-3 text-ink-gray-9': builderStore.leftPanelActiveTab === option.value,
					}"
					@click.stop="setActiveTab(option.value as LeftSidebarTabOption)">
					<FeatherIcon
						:name="option.icon"
						v-if="typeof option.icon === 'string'"
						class="size-4"></FeatherIcon>
					<component :is="option.icon" v-else />
				</button>
			</Tooltip>
		</div>
		<div
			class="no-scrollbar hover:show-scrollbar relative min-h-full overflow-auto"
			:style="{
				width: `${builderStore.builderLayout.leftPanelWidth}px`,
			}"
			@click.stop="
				builderStore.leftPanelActiveTab === 'Layers' && canvasStore.activeCanvas?.clearSelection()
			">
			<div v-show="builderStore.leftPanelActiveTab === 'Blocks'">
				<BuilderBlockTemplates class="mt-1 p-4 pt-3" />
			</div>
			<div v-show="builderStore.leftPanelActiveTab === 'Assets'">
				<BuilderAssets class="mt-1 p-4 pt-3" />
			</div>
			<div v-show="builderStore.leftPanelActiveTab === 'Layers'" class="p-3 pr-0">
				<span class="flex items-center gap-2 py-1 pb-2 text-sm capitalize text-ink-gray-4">
					<FeatherIcon
						:name="
							canvasStore.activeCanvas?.canvasProps.breakpoints.find(
								(b) => b.device === canvasStore.activeCanvas?.activeBreakpoint,
							)?.icon || 'monitor'
						"
						class="size-3" />
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
			<div v-show="builderStore.leftPanelActiveTab === 'Code'">
				<PageScript
					class="p-4"
					:key="pageStore.selectedPage"
					v-if="pageStore.selectedPage && pageStore.activePage"
					:page="pageStore.activePage" />
			</div>
		</div>

		<VariableManager v-model="showVariableManager" :container="miniSidebar" />
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import ComponentIcon from "@/components/Icons/Component.vue";
import LayersIcon from "@/components/Icons/Layers.vue";
import PlusIcon from "@/components/Icons/Plus.vue";
import VariableManager from "@/components/Modals/VariableManager.vue";
import PageScript from "@/components/PageScript.vue";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { Tooltip } from "frappe-ui";
import { inject, nextTick, Ref, ref, watch, watchEffect } from "vue";
import BlockLayers from "./BlockLayers.vue";
import BuilderAssets from "./BuilderAssets.vue";
import BuilderBlockTemplates from "./BuilderBlockTemplates.vue";
import BuilderCanvas from "./BuilderCanvas.vue";
import PanelResizer from "./PanelResizer.vue";

const showVariableManager = ref(false);
const miniSidebar = ref(null) as Ref<HTMLElement | null>;
const pageLayers = ref<InstanceType<typeof BlockLayers> | null>(null);
const componentLayers = ref<InstanceType<typeof BlockLayers> | null>(null);

const canvasStore = useCanvasStore();
const builderStore = useBuilderStore();
const pageStore = usePageStore();

const pageCanvas = inject("pageCanvas") as Ref<InstanceType<typeof BuilderCanvas> | null>;
const fragmentCanvas = inject("fragmentCanvas") as Ref<InstanceType<typeof BuilderCanvas> | null>;

const leftPanelOptions = [
	{
		label: "Insert",
		value: "Blocks",
		icon: PlusIcon,
	},
	{
		label: "Layers",
		value: "Layers",
		icon: LayersIcon,
	},
	{
		label: "Components",
		value: "Assets",
		icon: ComponentIcon,
	},
	{
		label: "Code",
		value: "Code",
		icon: "code",
	},
	{
		label: "Variables",
		value: "variables",
		icon: "aperture",
	},
];

const setActiveTab = (tab: LeftSidebarTabOption) => {
	if (tab === "variables") {
		showVariableManager.value = true;
	} else {
		builderStore.leftPanelActiveTab = tab;
	}
};

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
