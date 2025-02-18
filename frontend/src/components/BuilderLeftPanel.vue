<template>
	<div class="flex">
		<PanelResizer
			:dimension="store.builderLayout.leftPanelWidth"
			side="right"
			:maxDimension="500"
			@resize="(width) => (store.builderLayout.leftPanelWidth = width)" />
		<div class="flex min-h-full flex-col items-center gap-3 border-r border-outline-gray-1 p-3">
			<button
				v-for="option of leftPanelOptions"
				:key="option.value"
				class="flex size-8 items-center justify-center rounded text-ink-gray-7 hover:bg-surface-gray-2 focus:!bg-surface-gray-3"
				:class="{
					'bg-surface-gray-3 text-ink-gray-9': store.leftPanelActiveTab === option.value,
				}"
				@click.stop="setActiveTab(option.value as LeftSidebarTabOption)"
				:title="option.label">
				<FeatherIcon :name="option.icon" v-if="typeof option.icon === 'string'" class="size-4"></FeatherIcon>
				<component :is="option.icon" v-else />
			</button>
		</div>
		<div
			class="no-scrollbar relative min-h-full overflow-auto"
			:style="{
				width: `${store.builderLayout.leftPanelWidth}px`,
			}"
			@click.stop="store.leftPanelActiveTab === 'Layers' && store.activeCanvas?.clearSelection()">
			<div v-show="store.leftPanelActiveTab === 'Blocks'">
				<BuilderBlockTemplates class="mt-1 p-4 pt-3" />
			</div>
			<div v-show="store.leftPanelActiveTab === 'Assets'">
				<BuilderAssets class="mt-1 p-4 pt-3" />
			</div>
			<div v-show="store.leftPanelActiveTab === 'Layers'" class="p-3">
				<BlockLayers
					class="no-scrollbar overflow-auto"
					v-if="pageCanvas"
					:disable-draggable="true"
					ref="pageLayers"
					:blocks="[pageCanvas?.getRootBlock() as Block]"
					v-show="store.editingMode == 'page'" />
				<BlockLayers
					class="no-scrollbar overflow-auto"
					ref="componentLayers"
					:disable-draggable="true"
					:blocks="[fragmentCanvas?.getRootBlock()]"
					:indent="5"
					:adjustForRoot="false"
					v-if="store.editingMode === 'fragment' && fragmentCanvas" />
			</div>
			<div v-show="store.leftPanelActiveTab === 'Code'">
				<PageScript
					class="p-4"
					:key="store.selectedPage"
					v-if="store.selectedPage && store.activePage"
					:page="store.activePage" />
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import ComponentIcon from "@/components/Icons/Component.vue";
import LayersIcon from "@/components/Icons/Layers.vue";
import PlusIcon from "@/components/Icons/Plus.vue";
import PageScript from "@/components/PageScript.vue";
import Block from "@/utils/block";
import convertHTMLToBlocks from "@/utils/convertHTMLToBlocks";
import { createResource } from "frappe-ui";
import { Ref, inject, nextTick, ref, watch, watchEffect } from "vue";
import useStore from "../store";
import BlockLayers from "./BlockLayers.vue";
import BuilderAssets from "./BuilderAssets.vue";
import BuilderBlockTemplates from "./BuilderBlockTemplates.vue";
import BuilderCanvas from "./BuilderCanvas.vue";
import PanelResizer from "./PanelResizer.vue";

const pageCanvas = inject("pageCanvas") as Ref<InstanceType<typeof BuilderCanvas> | null>;
const fragmentCanvas = inject("fragmentCanvas") as Ref<InstanceType<typeof BuilderCanvas> | null>;

const prompt = ref(null) as unknown as Ref<string>;

const store = useStore();
const generating = ref(false);

const pageLayers = ref<InstanceType<typeof BlockLayers> | null>(null);
const componentLayers = ref<InstanceType<typeof BlockLayers> | null>(null);

watchEffect(() => {
	if (pageLayers.value) {
		store.activeLayers = pageLayers.value;
	} else if (componentLayers.value) {
		store.activeLayers = componentLayers.value;
	}
});

const leftPanelOptions = [
	{
		label: "Blocks",
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
];

const getPage = () => {
	generating.value = true;
	createResource({
		url: "builder.api.get_blocks",
		onSuccess(html: string) {
			store.clearBlocks();
			const blocks = convertHTMLToBlocks(html);
			store.pushBlocks([blocks]);
			generating.value = false;
		},
	}).submit({
		prompt: prompt.value,
	});
};

const setActiveTab = (tab: LeftSidebarTabOption) => {
	store.leftPanelActiveTab = tab;
};

// moved out of BlockLayers for performance
// TODO: Find a better way to do this
watch(
	() => store.hoveredBlock,
	() => {
		document.querySelectorAll(`[data-block-layer-id].hovered-block`).forEach((el) => {
			el.classList.remove("hovered-block");
		});
		if (store.hoveredBlock) {
			document.querySelector(`[data-block-layer-id="${store.hoveredBlock}"]`)?.classList.add("hovered-block");
		}
	},
);

watch(
	() => store.activeCanvas?.selectedBlockIds,
	async () => {
		await nextTick();
		const selectedBlocks = document.querySelectorAll(`[data-block-layer-id].block-selected`);
		selectedBlocks.forEach((el) => el.classList.remove("block-selected"));
		Array.from(store.activeCanvas?.selectedBlockIds || new Set([])).forEach((blockId: string) => {
			const blockElement = document.querySelector(`[data-block-layer-id="${blockId}"]`);
			blockElement?.classList.add("block-selected");
		});
	},
	{ deep: true },
);
</script>
