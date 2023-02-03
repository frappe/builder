<template>
	<div>
		<h3 class="mb-3 mt-8 text-gray-600 font-bold text-xs uppercase">Templates</h3>
		<draggable :list="components" :group="{ name: 'blocks', pull: 'clone', put: false }" item-key="id"
			:clone="handleClone" class="w-full flex flex-wrap">
			<template #item="{ element }">
				<div>
					<div class="flex items-center cursor-pointer justify-center
						h-10 w-10 border shadow-sm rounded-md mr-2 last:mr-0 mb-2 bg-white">
						<FeatherIcon :name="element.icon" class="h-5 text-gray-700" />
					</div>
					<p class="text-xs text-gray-800">{{ element.component_name }}</p>
				</div>
			</template>
		</draggable>
	</div>
</template>
<script setup>
import { ref } from "vue";
import draggable from "vuedraggable";
import { createListResource } from "frappe-ui";
const components = ref([]);

createListResource({
	doctype: "Web Page Component",
	fields: ["component_name", "icon", "block"],
	orderBy: "creation desc",
	start: 0,
	pageLength: 5,
	auto: true,
	onSuccess(data) {
		components.value = data;
	},
	transform(data) {
		data.forEach((d) => {
			d.block = JSON.parse(d.block);
			components.value.push(d);
		});
		return components;
	},
});

const handleClone = (item) => {
	const clonedItem = JSON.parse(JSON.stringify(item.block));
	// set unique id for each cloned item
	clonedItem.id = Math.random().toString(36).substr(2, 9);
	return clonedItem;
};
</script>
