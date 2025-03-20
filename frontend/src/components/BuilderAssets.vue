<template>
	<div class="flex flex-col gap-3">
		<div v-show="components.length > 10 || componentFilter">
			<BuilderInput
				type="text"
				placeholder="Search component"
				v-model="componentFilter"
				@input="
					(value: string) => {
						componentFilter = value;
					}
				" />
		</div>
		<div ref="componentContainer">
			<div v-show="!components.length" class="mt-2 text-base italic text-gray-600">No components saved</div>
			<div v-for="component in components" :key="component.name" class="flex w-full">
				<div class="component-container group relative flex w-full flex-col">
					<div
						class="user-component relative flex translate-x-0 translate-y-0 cursor-pointer items-center justify-between overflow-hidden truncate rounded border border-transparent bg-surface-white px-2 py-1.5"
						draggable="true"
						:data-component-id="component.component_id"
						:data-component-name="component.name"
						:class="{
							'!border-outline-gray-4':
								canvasStore.fragmentData.fragmentId === component.name ||
								componentStore.selectedComponent === component.component_id,
						}">
						<div class="flex items-center gap-2 text-ink-gray-7">
							<FeatherIcon :name="'box'" class="h-4 w-4"></FeatherIcon>
							<p class="text-base">
								{{ component.component_name }}
							</p>
						</div>
						<FeatherIcon
							name="trash"
							class="hidden h-3 w-3 cursor-pointer text-ink-gray-5 group-hover:block"
							@click.stop.prevent="componentStore.deleteComponent(component)"></FeatherIcon>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import webComponent from "@/data/webComponent";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import usePageStore from "@/stores/pageStore";
import { BuilderComponent } from "@/types/Builder/BuilderComponent";
import { useEventListener } from "@vueuse/core";
import { computed, onMounted, ref } from "vue";

const canvasStore = useCanvasStore();
const componentStore = useComponentStore();
const pageStore = usePageStore();

const componentFilter = ref("");
const componentContainer = ref(null);

onMounted(() => {
	webComponent.fetch();
});

const components = computed(() =>
	(webComponent.data || []).filter((d: BuilderComponent) => {
		if (d.for_web_page && d.for_web_page !== pageStore.selectedPage) {
			return false;
		}
		if (componentFilter.value) {
			return d.component_name?.toLowerCase().includes(componentFilter.value.toLowerCase());
		} else {
			return true;
		}
	}),
);

useEventListener(componentContainer, "click", (e) => {
	const component = (e.target as HTMLElement)?.closest(".user-component") as HTMLElement;
	if (component) {
		const componentStore = useComponentStore();
		const componentId = component.dataset.componentId as string;
		const componentName = component.dataset.componentName as string;
		componentStore.selectedComponent = componentId;
		// if in edit mode, open the component in editor
		if (canvasStore.fragmentData.fragmentId) {
			componentStore.editComponent(null, componentName);
		}
	}
});

useEventListener(componentContainer, "dragstart", (e) => {
	const component = (e.target as HTMLElement)?.closest(".user-component") as HTMLElement;
	if (component) {
		setComponentData(e, component.dataset.componentName as string);
		canvasStore.handleDragStart(e);
	}
});

useEventListener(componentContainer, "dragend", () => {
	canvasStore.handleDragEnd();
});

useEventListener(componentContainer, "dblclick", (e) => {
	const component = (e.target as HTMLElement)?.closest(".user-component") as HTMLElement;
	if (component) {
		const componentStore = useComponentStore();
		const componentName = component.dataset.componentName as string;
		componentStore.editComponent(null, componentName);
	}
});

const setComponentData = (ev: DragEvent, componentName: string) => {
	ev?.dataTransfer?.setData("componentName", componentName);
};
</script>
