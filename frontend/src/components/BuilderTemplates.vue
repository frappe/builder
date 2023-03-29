<template>
	<div>
		<h3 class="mb-3 text-gray-600 font-bold text-xs uppercase">Templates</h3>
		<draggable :list="components" :group="{ name: 'blocks', pull: 'clone', put: false }" item-key="id"
			:sort="false"
			:clone="(obj) => store.getBlockCopy(obj.block)" class="w-full flex flex-wrap">
			<template #item="{ element }">
				<div>
					<div class="flex items-center cursor-pointer justify-center
						h-8 w-16 border shadow-sm rounded-md mr-2 last:mr-0 mb-2 bg-white dark:bg-gray-800 dark:border-gray-700 dark:text-gray-200">
						<FeatherIcon :name="element.icon" class="h-4 text-gray-700 dark:text-gray-300" />
					</div>
					<p class="text-xs text-gray-800">{{ element.component_name }}</p>
				</div>
			</template>
		</draggable>
	</div>
</template>
<script setup>
import draggable from "vuedraggable";
import { createListResource } from "frappe-ui";
import useStore from "../store";
const store = useStore();
const components = store.components;
createListResource({
	doctype: "Web Page Component",
	fields: ["component_name", "icon", "block"],
	orderBy: "creation",
	start: 0,
	pageLength: 5,
	auto: true,
	onSuccess(data) {
		store.components = data;
	},
	transform(data) {
		data.forEach((d) => {
			d.block = JSON.parse(d.block);
		});
		return data;
	},
});
</script>
