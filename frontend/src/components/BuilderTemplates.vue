<template>
	<div>
		<h3 class="mb-3 text-gray-600 font-bold text-xs uppercase">Templates</h3>
		<draggable :list="components" :group="{ name: 'blocks', pull: 'clone', put: false }" item-key="id"
			:clone="(obj) => store.getBlockCopy(obj.block)" class="w-full flex flex-wrap">
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
import useStore from "../store";
const components = ref([]);
const store = useStore();
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
</script>
