<template>
	<div class="flex flex-col">
		<div class="sticky top-0 z-[1] flex items-center gap-2 bg-surface-base py-3">
			<BuilderInput
				v-show="showSearchInput"
				class="min-w-0 w-full flex-1"
				type="text"
				placeholder="Search Template"
				v-model="componentFilter"
				@input="
					(value: string) => {
						componentFilter = value;
					}
				" />
			<OptionToggle
				class="!w-fit [&>div]:w-fit [&>div]:min-w-0 [&>div>div]:w-fit [&>div>div>button]:px-2"
				:options="viewOptions"
				v-model="viewMode" />
		</div>
		<div v-show="!templateComponents.length" class="pt-2 text-base italic text-gray-600">No templates saved</div>
		<CollapsibleSection
			class="order-1"
			:sectionName="section.sectionName"
			v-for="section in sections"
			:key="section.sectionName">
			<div v-if="viewMode === 'grid'" class="grid auto-rows-[90px] grid-cols-2 gap-4">
				<div
					v-for="component in section.components"
					:key="component.name"
					class="flex"
					:class="{
						'col-span-2': component?.preview_width === 2,
						'row-span-2': component?.preview_height === 2,
					}">
					<div
						class="standard-component relative flex h-full w-full translate-x-0 translate-y-0 cursor-pointer flex-col items-center justify-center gap-2 overflow-hidden truncate rounded-md border border-transparent bg-surface-gray-1 p-2 pt-3"
						draggable="true"
						:data-component-id="component.component_id"
						:data-component-name="component.name"
						@click="selectComponent(component)"
						@dblclick="is_developer_mode && componentStore.editComponent(null, component.name)"
						@dragstart="(ev) => setComponentData(ev, component)"
						@dragend="() => canvasStore.handleDragEnd()">
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
					</div>
				</div>
			</div>
			<div v-else class="flex flex-col gap-1">
				<ItemListRow
					v-for="component in section.components"
					:key="component.name"
					class="standard-component w-full cursor-pointer bg-surface-base"
					draggable="true"
					:data-component-id="component.component_id"
					:data-component-name="component.name"
					:active="componentStore.selectedComponent === component.component_id"
					@click="selectComponent(component)"
					@dblclick="is_developer_mode && componentStore.editComponent(null, component.name)"
					@dragstart="(ev) => setComponentData(ev, component)"
					@dragend="() => canvasStore.handleDragEnd()">
					<template #prefix>
						<img
							v-if="component.preview"
							:src="component.preview"
							class="pointer-events-none size-5 rounded-sm object-contain" />
						<span v-else class="lucide-box size-3.5 text-ink-gray-5" aria-hidden="true" />
					</template>
					<span class="block truncate">{{ component.component_name }}</span>
				</ItemListRow>
			</div>
		</CollapsibleSection>
	</div>
</template>
<script setup lang="ts">
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import { builderComponentCategories, standardComponent } from "@/data/webComponent";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import { BuilderComponent } from "@/types/doctypes";
import { ItemListRow } from "frappe-ui";
import { computed, onMounted, ref } from "vue";
import CollapsibleSection from "./CollapsibleSection.vue";

const canvasStore = useCanvasStore();
const componentStore = useComponentStore();
const is_developer_mode = window.is_developer_mode;
const componentFilter = ref("");
const viewMode = ref<"grid" | "list">("grid");
const viewOptions = [
	{ label: "Grid", value: "grid", icon: "lucide-grid-2x2", hideLabel: true },
	{ label: "List", value: "list", icon: "lucide-list", hideLabel: true },
];

onMounted(() => {
	standardComponent.fetch();
	builderComponentCategories.fetch();
});

const templateComponents = computed(() => {
	return (standardComponent.data || [])
		.filter((d: BuilderComponent) => {
			if (!d.is_standard) {
				return false;
			}
			if (componentFilter.value) {
				return d.component_name?.toLowerCase().includes(componentFilter.value.toLowerCase());
			}
			return true;
		})
		.sort((a: BuilderComponent, b: BuilderComponent) => (a.sort_order || 0) - (b.sort_order || 0));
});

const showSearchInput = computed(() => {
	return templateComponents.value.length > 10 || componentFilter.value;
});

const setComponentData = (ev: DragEvent, component: BuilderComponent) => {
	ev.dataTransfer?.setData("componentName", component.name);
	canvasStore.handleDragStart(ev);
};

const selectComponent = (component: BuilderComponent) => {
	componentStore.selectedComponent = component.component_id || component.name;
	if (is_developer_mode && canvasStore.fragmentData.fragmentId) {
		componentStore.editComponent(null, component.name);
	}
};

const getFilteredComponents = (section: string) => {
	return templateComponents.value.filter((d: BuilderComponent) => (d.category || "Uncategorized") === section);
};

const sections = computed(() => {
	const categories = new Set<string>(builderComponentCategories.data || []);
	templateComponents.value.forEach((component: BuilderComponent) => {
		categories.add(component.category || "Uncategorized");
	});
	return Array.from(categories)
		.map((category: string) => {
			return {
				sectionName: category,
				components: getFilteredComponents(category) as BuilderComponent[],
			};
		})
		.filter((section) => section.components.length > 0);
});
</script>
