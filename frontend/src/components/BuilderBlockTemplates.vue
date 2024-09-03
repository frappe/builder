<template>
	<div class="flex flex-col gap-3">
		<div v-show="blockTemplates.length > 10 || blockTemplateFilter">
			<Input
				type="text"
				placeholder="Search component"
				v-model="blockTemplateFilter"
				@input="
					(value: string) => {
						blockTemplateFilter = value;
					}
				" />
		</div>
		<div class="grid grid-cols-2 gap-4">
			<div v-for="blockTemplate in blockTemplates" :key="blockTemplate.name" class="flex">
				<div
					class="relative flex h-24 w-full translate-x-0 translate-y-0 cursor-pointer flex-col items-center justify-center gap-2 overflow-hidden truncate rounded border border-transparent bg-gray-100 px-2 py-1.5 dark:bg-zinc-800"
					draggable="true"
					@click="is_developer_mode && store.editBlockTemplate(blockTemplate.name)"
					@dragstart="(ev) => setBlockTemplateData(ev, blockTemplate)">
					<div class="flex h-11 w-15 items-center justify-center">
						<img :src="blockTemplate.preview" class="text-gray-800 dark:text-zinc-400" />
					</div>
					<p class="text-sm text-gray-800 dark:text-zinc-400">
						{{ blockTemplate.template_name }}
					</p>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import builderBlockTemplate from "@/data/builderBlockTemplate";
import useStore from "@/store";
import { computed, ref } from "vue";
import Input from "./Input.vue";

const store = useStore();
const is_developer_mode = window.is_developer_mode;

const blockTemplateFilter = ref("");
const blockTemplates = computed(() => {
	return builderBlockTemplate.data.filter((d) => {
		if (blockTemplateFilter.value) {
			return d.name?.toLowerCase().includes(blockTemplateFilter.value.toLowerCase());
		} else {
			return true;
		}
	});
});

const setBlockTemplateData = (ev: DragEvent, component: BlockComponent) => {
	ev?.dataTransfer?.setData("blockTemplate", component.name);
};
</script>
