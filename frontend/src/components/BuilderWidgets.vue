<template>
	<div>
		<draggable
			:list="store.widgets"
			:sort="false"
			:group="{ name: 'blocks', pull: 'clone', put: false }"
			item-key="id"
			class="flex w-full flex-wrap"
			:clone="store.getBlockCopy">
			<template #item="{ element }">
				<div
					class="mb-2 mr-2 flex h-8 w-8 cursor-pointer items-center justify-center rounded-md border bg-white shadow-sm last:mr-0 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200">
					<FeatherIcon :name="element.icon" class="h-4 text-gray-700 dark:text-zinc-300" />
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
