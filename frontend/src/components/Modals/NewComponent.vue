<template>
	<Dialog
		style="z-index: 40"
		:options="{
			title: 'New Component',
			size: 'sm',
			actions: [
				{
					label: 'Save',
					variant: 'solid',
					onClick: createComponentHandler,
				},
			],
		}">
		<template #body-content>
			<BuilderInput
				type="text"
				:modelValue="componentName"
				@input="(value: string) => (componentName = value)"
				label="Component Name"
				required />
			<div class="mt-3">
				<BuilderInput
					class="text-sm [&>span]:!text-sm"
					type="checkbox"
					v-model="isGlobalComponent"
					label="Global Component" />
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import type Block from "@/block";
import Dialog from "@/components/Controls/Dialog.vue";
import webComponent from "@/data/webComponent";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import usePageStore from "@/stores/pageStore";
import { posthog } from "@/telemetry";
import { BuilderComponent } from "@/types/Builder/BuilderComponent";
import { getBlockCopy, getBlockString } from "@/utils/helpers";
import { ref } from "vue";

const componentStore = useComponentStore();
const canvasStore = useCanvasStore();
const pageStore = usePageStore();

const props = defineProps<{
	block: Block;
}>();

const componentName = ref("");
const isGlobalComponent = ref(0);

const createComponentHandler = async (context: { close: () => void }) => {
	// clean block with inherited or dynamic props
	const cleanBlock = props.block;
	if (props.block.props) {
		const cleanProps = cleanBlock.props || {};
		Object.entries(props.block.props).forEach(([key, value]) => {
			if (value.type === 'inherited' || value.type === 'dynamic') {
				cleanProps[key] = {...value, type: 'static' , value: null};
			}
		});
		cleanBlock.props = cleanProps;
	}

	const blockCopy = getBlockCopy(cleanBlock, true);
	blockCopy.removeStyle("left");
	blockCopy.removeStyle("top");
	blockCopy.removeStyle("position");
	const componentData = (await webComponent.insert.submit({
		block: getBlockString(blockCopy),
		component_name: componentName.value,
		for_web_page: isGlobalComponent.value ? null : pageStore.selectedPage,
	})) as BuilderComponent;
	posthog.capture("builder_component_created", { component_name: componentData.name });
	componentStore.setComponentMap(componentData);
	const block = canvasStore.activeCanvas?.findBlock(props.block.blockId);
	if (!block) return;
	block.extendFromComponent(componentData.name);
	componentName.value = "";
	isGlobalComponent.value = 0;
	context.close();
};
</script>
