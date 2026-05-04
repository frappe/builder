<template>
	<div class="flex flex-col">
		<div
			ref="componentContainer"
			class="order-1"
			:class="{
				'pt-2': !showSearchInput,
			}">
			<div v-show="!components.length" class="text-base italic text-gray-600">No components saved</div>
			<div v-for="component in components" :key="component.name" class="flex w-full">
				<div class="component-container group relative flex w-full flex-col">
					<div
						class="user-component relative flex translate-x-0 translate-y-0 cursor-pointer items-center justify-between overflow-hidden truncate rounded border border-transparent bg-surface-white py-1.5"
						draggable="true"
						:data-component-id="component.component_id"
						:data-component-name="component.name"
						@contextmenu.prevent="(e: MouseEvent) => showContextMenu(e, component)"
						:class="{
							'!border-outline-gray-4':
								canvasStore.fragmentData.fragmentId === component.name ||
								componentStore.selectedComponent === component.component_id,
						}">
						<div class="flex items-center gap-2 text-ink-gray-7">
							<Tooltip v-if="!component.for_web_page" text="Global Component" :hoverDelay="0.3">
								<FeatherIcon name="globe" class="size-4" />
							</Tooltip>
							<FeatherIcon v-else name="box" class="size-4" />
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
		<div v-show="showSearchInput" class="sticky top-0 -mb-1 bg-surface-white py-3">
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
		<ContextMenu ref="contextMenu" :options="contextMenuOptions" />
	</div>
</template>
<script setup lang="ts">
import ContextMenu from "@/components/ContextMenu.vue";
import webComponent from "@/data/webComponent";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import usePageStore from "@/stores/pageStore";
import { BuilderComponent } from "@/types/Builder/BuilderComponent";
import { useEventListener } from "@vueuse/core";
import { Tooltip } from "frappe-ui";
import { computed, onMounted, ref, Ref } from "vue";
import { toast } from "vue-sonner";

const canvasStore = useCanvasStore();
const componentStore = useComponentStore();
const pageStore = usePageStore();
const builderStore = useBuilderStore();

const componentFilter = ref("");
const componentContainer = ref(null);
const contextMenu = ref(null) as Ref<InstanceType<typeof ContextMenu> | null>;
const selectedComponent = ref(null) as Ref<BuilderComponent | null>;

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

const showContextMenu = (event: MouseEvent, component: BuilderComponent) => {
	if (!component.for_web_page) {
		contextMenu.value?.hide();
		return;
	}
	selectedComponent.value = component;
	contextMenu.value?.show(event);
};

const setAsGlobalComponent = () => {
	if (!selectedComponent.value) return;
	webComponent.setValue
		.submit({
			name: selectedComponent.value.name,
			for_web_page: null,
		})
		.then(() => {
			toast.success("Component is now set as global.");
			if (selectedComponent.value) {
				selectedComponent.value.for_web_page = undefined;
				componentStore.setComponentMap(selectedComponent.value);
			}
		});
};

const contextMenuOptions: ContextMenuOption[] = [
	{
		label: "Set as Global Component",
		action: setAsGlobalComponent,
		disabled: () => builderStore.readOnlyMode,
	},
];
</script>
