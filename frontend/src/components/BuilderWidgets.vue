<template>
	<div>
		<h3 class="mb-3 text-gray-600 font-bold text-xs uppercase">WIDGETS</h3>
		<draggable
			:list="store.widgets"
			:sort="false"
			:group="{ name: 'blocks', pull: 'clone', put: false }"
			item-key="id"
			class="w-full flex flex-wrap" :clone="handleClone">
			<template #item="{ element }">
				<div
					class="flex items-center cursor-pointer justify-center
					h-10 w-10 border shadow-sm rounded-md mr-2 last:mr-0 mb-2 bg-white">
					<FeatherIcon :name="element.icon" class="h-5 text-gray-700" />
				</div>
			</template>
		</draggable>
	</div>
</template>
<script setup>
import draggable from "vuedraggable";
import useStore from "../store";

const store = useStore();

const handleClone = (item) => {
	const clonedItem = JSON.parse(JSON.stringify(item));
	// set unique id for each cloned item
	clonedItem.id = Math.random().toString(36).substr(2, 9);
	return clonedItem;
};
</script>

<style>
@tailwind components;

@layer components {
	.Container {
		@apply bg-gray-300;
		@apply h-[300px];
		@apply w-full;
	}

	.Image {
		@apply bg-gray-600;
		@apply h-[300px];
		@apply w-full;
	}
}
</style>
