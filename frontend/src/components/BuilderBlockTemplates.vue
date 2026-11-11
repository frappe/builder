<template>
	<div class="flex flex-col">
		<CollapsibleSection
			class="order-1"
			:sectionName="__(section.category)"
			v-for="section in sections"
			:key="section.category">
			<div class="grid auto-rows-[90px] grid-cols-2 gap-4">
				<div
					v-for="blockTemplate in section.templates"
					:key="blockTemplate.name"
					class="flex"
					:class="{
						'col-span-2': blockTemplate?.preview_width === 2,
						'row-span-2': blockTemplate?.preview_height === 2,
					}">
					<BlockTemplateCard
						:label="blockTemplate.template_name"
						:preview="blockTemplate.preview"
						:wide="blockTemplate?.preview_width === 2"
						@click="selectBlockTemplate(blockTemplate)"
						@dblclick="is_developer_mode && blockTemplateStore.editBlockTemplate(blockTemplate.name)"
						@dragstart="(ev: DragEvent) => setBlockTemplateData(ev, blockTemplate)"
						@dragend="() => canvasStore.handleDragEnd()" />
				</div>
				<div v-for="template in section.pluginTemplates" :key="template.name" class="flex">
					<BlockTemplateCard
						:label="template.label"
						:preview="template.preview"
						:icon="template.icon"
						@click="insertBlock(template.getBlock())"
						@dragstart="(ev: DragEvent) => startBlockDrag(ev, template.getBlock())"
						@dragend="() => canvasStore.handleDragEnd()" />
				</div>
			</div>
		</CollapsibleSection>
		<div v-show="templateCount > 10 || blockTemplateFilter" class="sticky top-0 bg-surface-base py-3">
			<BuilderInput
				type="text"
				:placeholder="__('Search Template')"
				v-model="blockTemplateFilter"
				@input="
					(value: string) => {
						blockTemplateFilter = value;
					}
				" />
		</div>
	</div>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import BlockTemplateCard from "@/components/BlockTemplateCard.vue";
import { blockTemplates, getBlockTemplateSections } from "@/components/BlockTemplates";
import builderBlockTemplate from "@/data/builderBlockTemplate";
import { insertBlock, startBlockDrag } from "@/plugins/blocks";
import useBlockTemplateStore from "@/stores/blockTemplateStore";
import useCanvasStore from "@/stores/canvasStore";
import { BlockTemplate } from "@/types/doctypes";
import { computed, onMounted, ref } from "vue";
import CollapsibleSection from "./CollapsibleSection.vue";

const canvasStore = useCanvasStore();
const blockTemplateStore = useBlockTemplateStore();
const is_developer_mode = window.is_developer_mode;
const blockTemplateFilter = ref("");

onMounted(() => {
	builderBlockTemplate.fetch();
});

const templateCount = computed(
	() => (builderBlockTemplate.data || []).length + blockTemplates.visible.value.length,
);

const setBlockTemplateData = (ev: DragEvent, component: BlockTemplate) => {
	ev.dataTransfer?.setData("blockTemplate", component.name);
	canvasStore.handleDragStart(ev);
};

const selectedBlockTemplate = ref<string | null>(null);
const selectBlockTemplate = (blockTemplate: BlockTemplate) => {
	selectedBlockTemplate.value = blockTemplate.name;
	if (is_developer_mode && canvasStore.fragmentData.fragmentId) {
		blockTemplateStore.editBlockTemplate(blockTemplate.name);
	}
};

const sections = computed(() =>
	getBlockTemplateSections(
		blockTemplateStore.blockTemplateCategoryOptions as string[],
		builderBlockTemplate.data || [],
		blockTemplates.visible.value,
		blockTemplateFilter.value,
	),
);
</script>
