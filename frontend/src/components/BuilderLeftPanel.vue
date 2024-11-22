<template>
	<div class="flex">
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
			<PanelResizer
				:dimension="store.builderLayout.leftPanelWidth"
				side="right"
				:maxDimension="500"
				@resize="(width) => (store.builderLayout.leftPanelWidth = width)" />
			<div v-if="false" class="mb-5 flex flex-col overflow-hidden rounded-lg text-sm">
				<textarea
					class="no-scrollbar h-fit resize-none rounded-sm border-0 bg-gray-300 text-sm outline-none dark:bg-zinc-700 dark:text-white"
					v-model="prompt"
					:disabled="generating" />
				<button
					@click="getPage"
					type="button"
					class="bg-gray-300 p-2 text-gray-800 dark:bg-zinc-700 dark:text-zinc-300"
					:disabled="generating">
					Generate
				</button>
			</div>
			<div v-show="store.leftPanelActiveTab === 'Blocks'">
				<BuilderBlockTemplates class="mt-1 p-4 pt-3" />
			</div>
			<div v-show="store.leftPanelActiveTab === 'Assets'">
				<BuilderAssets class="mt-1 p-4 pt-3" />
			</div>
			<div v-show="store.leftPanelActiveTab === 'Layers'" class="p-4 pt-3">
				<BlockLayers
					class="no-scrollbar overflow-auto"
					v-if="pageCanvas"
					ref="pageLayers"
					:blocks="[pageCanvas?.getFirstBlock() as Block]"
					v-show="store.editingMode == 'page'" />
				<BlockLayers
					class="no-scrollbar overflow-auto"
					ref="componentLayers"
					:blocks="[fragmentCanvas?.getFirstBlock()]"
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
import { Ref, inject, ref, watch, watchEffect } from "vue";
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
	() => store.activeCanvas?.selectedBlocks,
	() => {
		document.querySelectorAll(`[data-block-layer-id].block-selected`).forEach((el) => {
			el.classList.remove("block-selected");
		});
		if (store.activeCanvas?.selectedBlocks.length) {
			store.activeCanvas?.selectedBlocks.forEach((block: Block) => {
				document.querySelector(`[data-block-layer-id="${block.blockId}"]`)?.classList.add("block-selected");
			});
		}
	},
);
</script>
