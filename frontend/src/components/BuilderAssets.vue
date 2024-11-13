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
		<div>
			<div v-show="!components.length" class="mt-2 text-base italic text-gray-600">No components saved</div>
			<div v-for="component in components" :key="component.name" class="flex w-full">
				<div class="component-container group relative flex w-full flex-col">
					<div
						class="relative flex translate-x-0 translate-y-0 cursor-pointer items-center justify-between overflow-hidden truncate rounded border border-transparent bg-surface-white px-2 py-1.5"
						draggable="true"
						:class="{
							'!border-gray-400 dark:!border-zinc-600':
								store.fragmentData.fragmentId === component.name ||
								selectedComponent === component.component_id,
						}"
						@click="selectComponent(component)"
						@dblclick="store.editComponent(null, component.name)"
						@dragstart="(ev) => setComponentData(ev, component)">
						<div class="flex items-center gap-2">
							<FeatherIcon :name="'box'" class="h-4 w-4 text-gray-800 dark:text-zinc-400"></FeatherIcon>
							<p class="text-base text-gray-800 dark:text-zinc-400">
								{{ component.component_name }}
							</p>
						</div>
						<FeatherIcon
							name="trash"
							class="hidden h-3 w-3 cursor-pointer text-gray-800 group-hover:block dark:text-zinc-400"
							@click.stop.prevent="deleteComponent(component)"></FeatherIcon>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import webComponent from "@/data/webComponent";
import useStore from "@/store";
import { BuilderComponent } from "@/types/Builder/BuilderComponent";
import { confirm } from "@/utils/helpers";
import { computed, onMounted, ref } from "vue";

const store = useStore();
const componentFilter = ref("");

onMounted(() => {
	// webComponent.fetch();
});

const components = computed(() =>
	(webComponent.data || []).filter((d: BuilderComponent) => {
		if (d.for_web_page && d.for_web_page !== store.selectedPage) {
			return false;
		}
		if (componentFilter.value) {
			return d.component_name?.toLowerCase().includes(componentFilter.value.toLowerCase());
		} else {
			return true;
		}
	}),
);

const deleteComponent = async (component: BlockComponent) => {
	if (store.isComponentUsed(component.name)) {
		alert("Component is used in current page. You cannot delete it.");
	} else {
		const confirmed = await confirm(
			`Are you sure you want to delete component: ${component.component_name}?`,
		);
		if (confirmed) {
			webComponent.delete.submit(component.name).then(() => {
				store.componentMap.delete(component.name);
			});
		}
	}
};

const setComponentData = (ev: DragEvent, component: BlockComponent) => {
	ev?.dataTransfer?.setData("componentName", component.name);
};

const selectedComponent = ref<string | null>(null);
const selectComponent = (component: BlockComponent) => {
	selectedComponent.value = component.component_id;
	// if in edit mode, open the component in editor
	if (store.fragmentData.fragmentId) {
		store.editComponent(null, component.name);
	}
};
</script>
