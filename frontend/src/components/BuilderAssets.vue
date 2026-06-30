<template>
	<div class="isolate flex flex-col">
		<div class="sticky top-0 z-[1] flex items-center gap-2 bg-surface-base py-3">
			<BuilderInput
				v-show="showSearchInput"
				class="min-w-0 flex-1"
				type="text"
				placeholder="Search component"
				v-model="componentFilter"
				@input="
					(value: string) => {
						componentFilter = value;
					}
				" />
			<OptionToggle
				class="!w-fit [&>div]:min-w-0 [&>div>div]:w-fit [&>div>div>button]:px-2"
				:options="viewOptions"
				v-if="components.length"
				v-model="viewMode" />
		</div>
		<div
			ref="componentContainer"
			:class="{
				'pt-2': !showSearchInput,
			}">
			<div v-show="!components.length" class="text-base italic text-gray-600">No components {{ componentFilter ? "found" : "saved" }}</div>
			<CollapsibleSection
				v-for="section in sections"
				:key="section.sectionName"
				class="order-1"
				:sectionName="section.sectionName">
				<div v-if="viewMode === 'grid'" class="grid auto-rows-[90px] grid-cols-2 gap-4">
					<div
						v-for="component in section.components"
						:key="component.name"
						class="group flex w-full"
						:class="{
							'col-span-2': component?.preview_width === 2,
							'row-span-2': component?.preview_height === 2,
						}">
						<div
							class="user-component relative flex h-full w-full cursor-pointer flex-col items-center justify-center gap-2 overflow-hidden rounded-md border border-transparent bg-surface-gray-1 p-2 pt-3"
							:class="{
								'!bg-surface-gray-3':
									canvasStore.fragmentData.fragmentId === component.name ||
									componentStore.selectedComponent === component.component_id,
							}"
							draggable="true"
							:data-component-id="component.component_id"
							:data-component-name="component.name">
							<div
								class="flex h-4/5 items-center justify-center"
								:class="{
									'w-14': !component?.preview_width || component?.preview_width == 1,
								}">
								<img
									v-if="component.preview"
									:src="component.preview"
									class="pointer-events-none max-h-full max-w-full object-contain" />
								<span v-else class="lucide-box size-5 text-ink-gray-5" aria-hidden="true" />
							</div>
							<p class="text-wrap text-center text-sm text-ink-gray-6">
								{{ component.component_name }}
							</p>
							<span
								class="lucide-trash absolute right-2 top-2 size-3 cursor-pointer text-ink-gray-5"
								:class="draggingComponentName === component.name ? 'hidden' : 'hidden group-hover:block'"
								aria-hidden="true"
								@click.stop.prevent="componentStore.deleteComponent(component)" />
						</div>
					</div>
				</div>
				<div v-else class="flex flex-col gap-1">
					<ItemListRow
						v-for="component in section.components"
						:key="component.name"
						class="user-component group w-full cursor-pointer bg-surface-base"
						:class="{
							'!bg-surface-gray-3':
								canvasStore.fragmentData.fragmentId === component.name ||
								componentStore.selectedComponent === component.component_id,
						}"
						draggable="true"
						:data-component-id="component.component_id"
						:data-component-name="component.name"
						:active="
							canvasStore.fragmentData.fragmentId === component.name ||
							componentStore.selectedComponent === component.component_id
						">
						<template #prefix>
							<img
								v-if="component.preview"
								:src="component.preview"
								class="pointer-events-none size-5 rounded-sm object-contain" />
							<span v-else class="lucide-box size-3.5 text-ink-gray-5" aria-hidden="true" />
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
			</CollapsibleSection>
		</div>
	</div>
</template>
<script setup lang="ts">
import CollapsibleSection from "@/components/CollapsibleSection.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
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
const viewMode = ref<"grid" | "list">("grid");
const viewOptions = [
	{ label: "Grid", value: "grid", icon: "lucide-grid-2x2", hideLabel: true },
	{ label: "List", value: "list", icon: "lucide-list", hideLabel: true },
];

const showSearchInput = computed(() => {
	return components.value.length || componentFilter.value;
});

onMounted(() => {
	webComponent.fetch();
});

const components = computed(() =>
	(webComponent.data || []).filter((d: BuilderComponent) => {
		if (d.is_standard) {
			return false;
		}
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

const getFilteredComponents = (section: string) => {
	return components.value.filter((component: BuilderComponent) => (component.category || "Uncategorized") === section);
};

const sections = computed(() => {
	const categories = new Set<string>();
	components.value.forEach((component: BuilderComponent) => {
		categories.add(component.category || "Uncategorized");
	});
	return Array.from(categories).map((category) => ({
		sectionName: category,
		components: getFilteredComponents(category),
	}));
});

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
