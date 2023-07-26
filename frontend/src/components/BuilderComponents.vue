<template>
	<div>
		<div v-if="!Object.keys(store.components).length" class="text-sm italic text-gray-600">
			No components saved
		</div>
		<div
			:list="store.components"
			v-for="component in store.components"
			:key="component.name"
			class="flex w-full flex-wrap">
			<div class="group relative mb-3 w-full">
				<div
					class="relative mb-1 mr-2 flex h-24 w-full max-w-[300px] cursor-pointer items-center justify-center overflow-hidden rounded-md border bg-gray-50 p-2 shadow-sm last:mr-0 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
					draggable="true"
					@dragstart="(ev) => setData(ev, component)">
					<div
						class="pointer-events-none absolute flex w-[1400px] justify-center self-center"
						:style="{
							transform: 'scale(' + component.scale + ')',
						}">
						<BuilderBlock class="!static" :block="component.block" :preview="true" />
					</div>
				</div>
				<p class="text-xs text-gray-800 dark:text-zinc-500">
					{{ component.component_name }}
				</p>
				<FeatherIcon
					name="trash"
					class="absolute right-2 top-2 hidden h-7 w-7 cursor-pointer rounded bg-white p-2 group-hover:block"
					@click.stop.prevent="deleteComponent(component)"></FeatherIcon>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import { createListResource } from "frappe-ui";
import useStore from "../store";
import BuilderBlock from "./BuilderBlock.vue";

const store = useStore();

const componentResource = createListResource({
	doctype: "Web Page Component",
	fields: ["component_name", "icon", "block", "name"],
	orderBy: "creation",
	start: 0,
	pageLength: 100,
	auto: true,
	transform(data: any[]) {
		data.forEach((d) => {
			d.block = store.getBlockCopy(JSON.parse(d.block));
			d.scale = 0.2;
		});
		return data;
	},
	onSuccess(data: BlockComponent[]) {
		store.components = data;
	},
});

const setScale = async (el: HTMLElement, block: BlockOptions) => {
	const scale = Math.max(Math.min(250 / el.offsetWidth, 80 / el.offsetHeight, 0.6), 0.1);
	block.scale = scale;
};

const deleteComponent = async (component: BlockComponent) => {
	const confirmed = await confirm(`Are you sure you want to delete component: ${component.component_name}?`);
	if (confirmed) {
		componentResource.delete.submit(component.name);
	}
};

const setData = (ev: DragEvent, component: BlockComponent) => {
	const blockCopy = store.getBlockCopy(component.block);
	ev?.dataTransfer?.setData("text/plain", JSON.stringify(blockCopy));
};
</script>
