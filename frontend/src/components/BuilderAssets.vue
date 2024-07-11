<template>
	<div class="flex flex-col gap-3">
		<CollapsibleSection :sectionName="'Block Templates'">
			<div v-show="blockTemplates.length > 10 || blockTemplateFilter">
				<Input
					type="text"
					placeholder="Search component"
					v-model="blockTemplateFilter"
					@input="
						(value: string) => {
							blockTemplateFilter = value;
						}
					" />
			</div>
			<div class="grid grid-cols-2 gap-4">
				<div v-for="blockTemplate in blockTemplates" :key="blockTemplate.name" class="flex">
					<div
						class="relative flex h-28 w-full translate-x-0 translate-y-0 cursor-pointer flex-col items-center justify-center gap-2 overflow-hidden truncate rounded border border-transparent bg-gray-100 px-2 py-1.5 dark:bg-zinc-800"
						draggable="true"
						@click="is_developer_mode && store.editBlockTemplate(blockTemplate.name)"
						@dragstart="(ev) => setBlockTemplateData(ev, blockTemplate)">
						<div class="flex h-16 w-16 items-center justify-center">
							<img :src="blockTemplate.preview" class="text-gray-800 dark:text-zinc-400" />
						</div>
						<p class="text-sm text-gray-800 dark:text-zinc-400">
							{{ blockTemplate.template_name }}
						</p>
					</div>
				</div>
			</div>
		</CollapsibleSection>
		<CollapsibleSection :sectionName="'Components'">
			<div v-show="components.length > 10 || componentFilter">
				<Input
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
							class="relative flex translate-x-0 translate-y-0 cursor-pointer items-center justify-between overflow-hidden truncate rounded border border-transparent bg-white px-2 py-1.5 dark:bg-zinc-900"
							draggable="true"
							:class="{
								'!border-gray-400 dark:!border-zinc-600':
									store.fragmentData.fragmentName === component.component_name,
							}"
							@click="store.editComponent(null, component.name)"
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
		</CollapsibleSection>
	</div>
</template>
<script setup lang="ts">
import builderBlockTemplate from "@/data/builderBlockTemplate";
import webComponent from "@/data/webComponent";
import useStore from "@/store";
import { BuilderComponent } from "@/types/Builder/BuilderComponent";
import { confirm } from "@/utils/helpers";
import { computed, ref } from "vue";
import CollapsibleSection from "./CollapsibleSection.vue";
import Input from "./Input.vue";

const store = useStore();
const componentFilter = ref("");
const is_developer_mode = window.is_developer_mode;

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

const blockTemplateFilter = ref("");
const blockTemplates = computed(() => {
	return builderBlockTemplate.data.filter((d) => {
		if (blockTemplateFilter.value) {
			return d.name?.toLowerCase().includes(blockTemplateFilter.value.toLowerCase());
		} else {
			return true;
		}
	});
});

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

const setBlockTemplateData = (ev: DragEvent, component: BlockComponent) => {
	ev?.dataTransfer?.setData("blockTemplate", component.name);
};
</script>
