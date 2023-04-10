<template>
	<div>
		<h3 class="mb-4 text-xs font-bold uppercase text-gray-600">Templates</h3>
		<draggable
			:list="store.components"
			:group="{ name: 'blocks', pull: 'clone', put: false }"
			item-key="id"
			:sort="false"
			:clone="(obj) => store.getBlockCopy(obj.block)"
			class="flex w-full flex-wrap">
			<template #item="{ element }">
				<div class="mb-3">
					<div
						class="relative mr-2 mb-1 flex h-24 w-48 cursor-pointer items-center justify-center overflow-hidden rounded-md border bg-gray-50 p-2 shadow-sm last:mr-0 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200">
						<div
							class="pointer-events-none absolute w-[1200px]"
							:style="{
								transform: 'scale(' + element.scale + ')',
							}">
							<BuilderBlock
								:element-properties="store.getBlockCopy(element.block)"
								ref="preview"
								@render-complete="(el) => setScale(el, element)"
								preview="true" />
						</div>
					</div>
					<p class="text-xs text-gray-800 dark:text-zinc-500">
						{{ element.component_name }}
					</p>
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
	pageLength: 10,
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
	const scale = Math.min(140 / el.offsetWidth, 70 / el.offsetHeight, 0.6);
	block.scale = scale;
};
</script>
