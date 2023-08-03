<template>
	<div>
		<div v-if="!components.length" class="text-sm italic text-gray-600">No components saved</div>
		<div v-for="component in components" :key="component.name" class="flex w-full flex-wrap">
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
						<BuilderBlock
							class="!static !m-0 h-fit max-w-fit !items-center !justify-center"
							:block="component.block"
							@mounted="($el) => setScale($el, component)"
							:preview="true" />
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
import { computed, nextTick } from "vue";
import BuilderBlock from "./BuilderBlock.vue";

import webComponent from "@/data/webComponent";

import useStore from "@/store";
import { WebPageComponent } from "@/types/WebsiteBuilder/WebPageComponent";
const store = useStore();

const components = computed(() =>
	(webComponent.data || []).filter(
		(d: WebPageComponent) => !d.for_web_page || d.for_web_page === store.builderState.selectedPage
	)
);

const setScale = async (el: HTMLElement, block: BlockOptions) => {
	nextTick(() => {
		const scale = Math.max(Math.min(60 / el.offsetHeight, 200 / el.offsetWidth), 0.1);
		block.scale = scale;
	});
};

const deleteComponent = async (component: BlockComponent) => {
	if (store.isComponentUsed(component.name)) {
		alert("Component is used in a page. You cannot delete it.");
	} else {
		const confirmed = await confirm(
			`Are you sure you want to delete component: ${component.component_name}?`
		);
		if (confirmed) {
			webComponent.delete.submit(component.name);
		}
	}
};

const setData = (ev: DragEvent, component: BlockComponent) => {
	ev?.dataTransfer?.setData("componentName", component.name);
};
</script>
