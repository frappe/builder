<template>
	<div class="isolate flex flex-col">
		<div v-show="showSearchInput" class="sticky top-0 z-[1] bg-surface-white py-3">
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
		<div
			ref="componentContainer"
			:class="{
				'pt-2': !showSearchInput,
			}">
			<div v-show="!components.length" class="text-base italic text-gray-600">No components saved</div>
			<div v-for="component in components" :key="component.name" class="group flex w-full">
				<ItemListRow
					class="user-component w-full cursor-pointer bg-surface-white"
					:class="{
						'!bg-surface-gray-3': canvasStore.fragmentData.fragmentId === component.name,
					}"
					draggable="true"
					:data-component-id="component.component_id"
					:data-component-name="component.name"
					:active="
						canvasStore.fragmentData.fragmentId === component.name ||
						componentStore.selectedComponent === component.component_id
					">
					<template #prefix>
						<span class="lucide-box size-3.5" aria-hidden="true" />
					</template>
					<span class="block truncate">{{ component.component_name }}</span>
					<template #suffix>
						<span
							class="lucide-trash size-3 cursor-pointer text-ink-gray-5"
							:class="draggingComponentName === component.name ? 'hidden' : 'hidden group-hover:block'"
							aria-hidden="true"
							@click.stop.prevent="componentStore.deleteComponent(component)" />
					</template>
				</ItemListRow>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import webComponent from "@/data/webComponent";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import usePageStore from "@/stores/pageStore";
import { BuilderComponent } from "@/types/doctypes";
import { useEventListener } from "@vueuse/core";
import { ItemListRow } from "frappe-ui";
import { computed, onMounted, ref } from "vue";

const canvasStore = useCanvasStore();
const componentStore = useComponentStore();
const pageStore = usePageStore();

const componentFilter = ref("");
const componentContainer = ref(null);
const draggingComponentName = ref<string | null>(null);

const showSearchInput = computed(() => {
	return components.value.length > 10 || componentFilter.value;
});

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
		draggingComponentName.value = component.dataset.componentName as string;
		canvasStore.handleDragStart(e);
	}
});

useEventListener(componentContainer, "dragend", () => {
	draggingComponentName.value = null;
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
