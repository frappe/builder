<template>
	<div>
		<h3 class="mb-4 text-gray-600 font-bold text-xs uppercase">Templates</h3>
		<draggable :list="store.components" :group="{ name: 'blocks', pull: 'clone', put: false }" item-key="id"
			:sort="false"
			:clone="(obj) => store.getBlockCopy(obj.block)" class="w-full flex flex-wrap">
			<template #item="{ element }">
				<div class="mb-3">
					<div class="flex items-center cursor-pointer justify-center
								h-24 w-48 border-2 shadow-sm rounded-md mr-2 last:mr-0 mb-1 bg-white
								dark:bg-zinc-800 dark:border-zinc-700 dark:text-zinc-200
								overflow-hidden relative p-2">
						<div class="absolute pointer-events-none w-[1200px]" :style="{
							'transform': 'scale(' + element.scale + ')'
						}">
							<BuilderBlock :element-properties="store.getBlockCopy(element.block)" ref="preview"
								@render-complete="(el) => setScale(el, element)" preview="true">
							</BuilderBlock>
						</div>
					</div>
					<p class="text-xs text-gray-800 dark:text-zinc-500">{{ element.component_name }}</p>
				</div>
			</template>
		</draggable>
	</div>
</template>
<script setup>
import draggable from "vuedraggable";
import { createListResource } from "frappe-ui";
import BuilderBlock from "./BuilderBlock.vue";
import useStore from "../store";
import { ref } from "vue";

const store = useStore();
const preview = ref(null);

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
			d.scale = 0.3; // for preview
		});
		return data;
	},
});

const setScale = (el, block) => {
	const scale = Math.min(140 / (el.offsetWidth), 70 / (el.offsetHeight), 0.6);
	block.scale = scale;
};
</script>
