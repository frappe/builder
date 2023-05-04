<template>
	<div>
		<draggable
			:list="store.widgets"
			:sort="false"
			:group="{ name: 'blocks', pull: 'clone', put: false }"
			item-key="id"
			class="w-full flex flex-wrap" :clone="store.getBlockCopy">
			<template #item="{ element }">
				<div
					class="flex items-center cursor-pointer justify-center
					h-8 w-8 border shadow-sm rounded-md mr-2 last:mr-0 mb-2 bg-white dark:bg-zinc-800 dark:border-zinc-700 dark:text-zinc-200">
					<FeatherIcon :name="element.icon" class="h-4 text-gray-700 dark:text-zinc-300"/>
				</div>
			</template>
		</draggable>
	</div>
</template>
<script setup lang="ts">
import draggable from "vuedraggable";
import useStore from "../store";
const store = useStore();
</script>

