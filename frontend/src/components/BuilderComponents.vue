<template>
	<div>
		<div class="mb-8" v-show="components.length || filter">
			<Input
				class="rounded-md text-sm text-gray-800 focus:ring-0 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:focus:bg-zinc-700"
				type="text"
				placeholder="Filter"
				inputClass="w-full"
				v-model="filter"
				@input="
					(value: string) => {
						filter = value;
					}
				" />
		</div>
		<div v-show="!components.length" class="text-sm italic text-gray-600">No components saved</div>
		<div v-for="component in components" :key="component.name" class="flex w-full flex-wrap">
			<div class="component-container group relative mb-3 w-full">
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
import webComponent from "@/data/webComponent";
import useStore from "@/store";
import { BuilderComponent } from "@/types/WebsiteBuilder/BuilderComponent";
import { useIntersectionObserver } from "@vueuse/core";
import { computed, ref } from "vue";
import BuilderBlock from "./BuilderBlock.vue";

const store = useStore();
const filter = ref("");

const components = computed(() =>
	(webComponent.data || []).filter((d: BuilderComponent) => {
		if (d.for_web_page && d.for_web_page !== store.getActivePage?.name) {
			return false;
		}
		if (filter.value) {
			return d.component_name?.toLowerCase().includes(filter.value.toLowerCase());
		} else {
			return true;
		}
	})
);

const setScale = async (el: HTMLElement, block: BlockOptions) => {
	// set scale to fit in container
	// setting scale when element is on screen
	const { stop } = useIntersectionObserver(
		el.closest(".component-container") as HTMLElement,
		([{ isIntersecting }], observerElement) => {
			if (isIntersecting) {
				const scale = Math.max(Math.min(60 / el.offsetHeight, 200 / el.offsetWidth), 0.1);
				block.scale = scale;
				stop();
			}
		}
	);
};

const deleteComponent = async (component: BlockComponent) => {
	if (store.isComponentUsed(component.name)) {
		alert("Component is used in current page. You cannot delete it.");
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
