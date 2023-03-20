<template>
	<div>
		<h3 class="mb-3 text-gray-600 font-bold text-xs uppercase">WIDGETS</h3>
		<draggable
			:list="store.widgets"
			:sort="false"
			:group="{ name: 'blocks', pull: 'clone', put: false }"
			item-key="id"
			class="w-full flex flex-wrap" :clone="store.getBlockCopy">
			<template #item="{ element }">
				<div
					class="flex items-center cursor-pointer justify-center
					h-8 w-8 border shadow-sm rounded-md mr-2 last:mr-0 mb-2 bg-white dark:bg-gray-800 dark:border-gray-700">
					<FeatherIcon :name="element.icon" class="h-4 text-gray-700 dark:text-gray-300"/>
				</div>
			</template>
		</draggable>
	</div>
</template>
<script setup>
import draggable from "vuedraggable";
import useStore from "../store";
const store = useStore();
</script>

