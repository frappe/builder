<template>
	<div>
		<BuilderInput
			class="query"
			type="text"
			placeholder="Search"
			autofocus
			v-model="query"
			@input="setQuery"></BuilderInput>
		<!-- <div class="flex w-full gap-2 text-sm">
			<Badge
				v-for="filter in filters"
				:label="filter.name"
				theme="gray"
				:variant="filter.selected ? 'solid' : 'outline'"
				size="md"
				class="mt-2 cursor-pointer" />
		</div> -->
		<div v-for="result in results">
			<div
				class="mt-2 flex cursor-pointer rounded px-2 py-1 text-sm text-ink-gray-7 hover:bg-surface-gray-1"
				@mouseover.stop="canvasStore.activeCanvas?.setHoveredBlock(result.blockId)"
				@click="canvasStore.activeCanvas?.scrollBlockIntoView(result)">
				{{ result.getBlockDescription() }}
			</div>
		</div>
		<div
			v-if="results.length === 0 && query"
			class="mt-4 flex h-full w-full items-center justify-center text-sm text-ink-gray-3">
			No results found
		</div>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import { watchDebounced } from "@vueuse/core";
import Badge from "frappe-ui/src/components/Badge.vue";
import { Ref, ref } from "vue";

const canvasStore = useCanvasStore();

const query = ref("");
const results = ref([]) as Ref<Block[]>;
const filters = ref([
	{
		name: "Tag",
		selected: false,
	},
	{
		name: "Content",
		selected: false,
	},
	{
		name: "Style",
		selected: false,
	},
	{
		name: "Attributes",
		selected: false,
	},
]);

const setQuery = (value: string) => {
	query.value = value;
};

watchDebounced(
	query,
	(val) => {
		results.value = [];
		if (val) {
			const filteredBlocks = canvasStore.activeCanvas?.searchBlock(val, null, 20);
			if (filteredBlocks?.length) {
				results.value = filteredBlocks;
			}
		}
	},
	{
		debounce: 300,
	},
);
</script>
