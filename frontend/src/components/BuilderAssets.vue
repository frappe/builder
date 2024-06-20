<template>
	<div class="flex flex-col">
		<CollapsibleSection :sectionName="'Components'">
			<div v-show="components.length > 10 || filter">
				<Input
					type="text"
					placeholder="Search component"
					v-model="filter"
					@input="
						(value: string) => {
							filter = value;
						}
					" />
			</div>
			<div>
				<div v-show="!components.length" class="mt-2 text-sm italic text-gray-600">No components saved</div>
				<div v-for="component in components" :key="component.name" class="flex w-full">
					<div class="component-container group relative flex w-full flex-col">
						<div
							class="relative flex translate-x-0 translate-y-0 cursor-pointer items-center justify-between overflow-hidden truncate rounded border border-transparent bg-white px-2 py-1.5 dark:bg-zinc-900"
							draggable="true"
							:class="{
								'!border-gray-400 dark:!border-zinc-600': store.editingComponent === component.name,
							}"
							@click="store.selectComponent(component.name)"
							@dragstart="(ev) => setData(ev, component)">
							<div class="flex items-center gap-2">
								<FeatherIcon :name="'box'" class="h-4 w-4 text-gray-800 dark:text-zinc-400"></FeatherIcon>
								<p class="text-xs text-gray-800 dark:text-zinc-400">
									{{ component.component_name }}
								</p>
							</div>
							<FeatherIcon
								name="x"
								class="hidden h-4 w-4 cursor-pointer text-gray-800 group-hover:block dark:text-zinc-400"
								@click.stop.prevent="deleteComponent(component)"></FeatherIcon>
						</div>
					</div>
				</div>
			</div>
		</CollapsibleSection>
	</div>
</template>
<script setup lang="ts">
import webComponent from "@/data/webComponent";
import useStore from "@/store";
import { BuilderComponent } from "@/types/Builder/BuilderComponent";
import { confirm } from "@/utils/helpers";
import { computed, ref } from "vue";
import CollapsibleSection from "./CollapsibleSection.vue";
import Input from "./Input.vue";

const store = useStore();
const filter = ref("");

const components = computed(() =>
	(webComponent.data || []).filter((d: BuilderComponent) => {
		if (d.for_web_page && d.for_web_page !== store.selectedPage) {
			return false;
		}
		if (filter.value) {
			return d.component_name?.toLowerCase().includes(filter.value.toLowerCase());
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
			webComponent.delete.submit(component.name);
		}
	}
};

const setData = (ev: DragEvent, component: BlockComponent) => {
	ev?.dataTransfer?.setData("componentName", component.name);
};
</script>
