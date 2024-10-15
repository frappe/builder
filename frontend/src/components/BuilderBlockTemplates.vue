<template>
	<div class="flex flex-col gap-3">
		<div v-show="blockTemplates.length > 10 || blockTemplateFilter">
			<BuilderInput
				type="text"
				placeholder="Search Template"
				v-model="blockTemplateFilter"
				@input="
					(value: string) => {
						blockTemplateFilter = value;
					}
				" />
		</div>
		<CollapsibleSection :sectionName="section.sectionName" v-for="section in sections">
			<div class="grid auto-rows-[80px] grid-cols-2 gap-4">
				<div
					v-for="blockTemplate in section.blocks"
					:key="blockTemplate.name"
					class="flex"
					:class="{
						'col-span-2': blockTemplate?.preview_width === 2,
						'row-span-2': blockTemplate?.preview_height === 2,
					}">
					<div
						class="relative flex h-full w-full translate-x-0 translate-y-0 cursor-pointer flex-col items-center justify-center gap-2 overflow-hidden truncate rounded-md border border-transparent bg-surface-gray-1 p-2 pt-3"
						draggable="true"
						@click="selectBlockTemplate(blockTemplate)"
						@dblclick="is_developer_mode && store.editBlockTemplate(blockTemplate.name)"
						@dragstart="(ev) => setBlockTemplateData(ev, blockTemplate)">
						<div
							class="flex h-4/5 items-center justify-center"
							:class="{
								'w-14': !blockTemplate?.preview_width || blockTemplate?.preview_width == 1,
							}">
							<img :src="blockTemplate.preview" />
						</div>
						<p class="text-sm text-text-icons-gray-6">
							{{ blockTemplate.template_name }}
						</p>
					</div>
				</div>
			</div>
		</CollapsibleSection>
	</div>
</template>
<script setup lang="ts">
import builderBlockTemplate from "@/data/builderBlockTemplate";
import useStore from "@/store";
import { BlockTemplate } from "@/types/Builder/BlockTemplate";
import { computed, onMounted, ref } from "vue";
import CollapsibleSection from "./CollapsibleSection.vue";

const store = useStore();
const is_developer_mode = window.is_developer_mode;
const blockTemplateFilter = ref("");

onMounted(() => {
	builderBlockTemplate.fetch();
});

const blockTemplates = computed(() => {
	return (builderBlockTemplate.data || []).filter((d: BlockTemplate) => {
		if (blockTemplateFilter.value) {
			return d.name?.toLowerCase().includes(blockTemplateFilter.value.toLowerCase());
		} else {
			return true;
		}
	});
});

const setBlockTemplateData = (ev: DragEvent, component: BlockTemplate) => {
	ev?.dataTransfer?.setData("blockTemplate", component.name);
};

const selectedBlockTemplate = ref<string | null>(null);
const selectBlockTemplate = (blockTemplate: BlockTemplate) => {
	selectedBlockTemplate.value = blockTemplate.name;
	if (is_developer_mode && store.fragmentData.fragmentId) {
		store.editBlockTemplate(blockTemplate.name);
	}
};

const getFilteredBlockTemplates = (section: string) => {
	return blockTemplates.value.filter((d: BlockTemplate) => d.category === section);
};

const sections = computed(() => {
	const categories = store.blockTemplateCategoryOptions as string[];
	return categories
		.map((category) => {
			return {
				sectionName: category as string,
				blocks: getFilteredBlockTemplates(category) as BlockTemplate[],
			};
		})
		.filter((section) => section.blocks.length > 0);
});
</script>
