<template>
	<div>
		<h3 class="mb-3 mt-8 text-gray-600 font-bold text-xs uppercase">Templates</h3>
		<draggable :list="templates"
			:group="{ name: 'blocks', pull: 'clone', put: false }"
			item-key="id"
			class="w-full flex flex-wrap">
			<template #item="{ element }">
				<div
					class="flex items-center cursor-pointer justify-center
					h-10 w-10 border shadow-sm rounded-md mr-2 last:mr-0 mb-2 bg-white"
					>
					<FeatherIcon :name="element.icon" class="h-5 text-gray-700" />
				</div>
			</template>
		</draggable>
	</div>
</template>
<script setup>
import { ref } from "vue";
import draggable from "vuedraggable";

const templates = ref([
	{
		template: "Navbar",
		icon: "menu",
		blocks: [
			{
				element: "nav",
				attributes: {
					class: "bg-gray-800",
				},
			},
		],
	},
]);
</script>
