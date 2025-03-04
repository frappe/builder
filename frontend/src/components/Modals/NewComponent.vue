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
import Dialog from "@/components/Controls/Dialog.vue";
import webComponent from "@/data/webComponent";
import useStore from "@/store";
import { posthog } from "@/telemetry";
import { BuilderComponent } from "@/types/Builder/BuilderComponent";
import Block from "@/utils/block";
import { getBlockCopy, getBlockString } from "@/utils/helpers";
import useComponentStore from "@/utils/useComponentStore";
import { ref } from "vue";

const store = useStore();
const componentStore = useComponentStore();

const props = defineProps<{
	block: Block;
}>();

const componentName = ref("");
const isGlobalComponent = ref(0);

const createComponentHandler = async (context: { close: () => void }) => {
	const blockCopy = getBlockCopy(props.block, true);
	blockCopy.removeStyle("left");
	blockCopy.removeStyle("top");
	blockCopy.removeStyle("position");
	const componentData = (await webComponent.insert.submit({
		block: getBlockString(blockCopy),
		component_name: componentName.value,
		for_web_page: isGlobalComponent.value ? null : store.selectedPage,
	})) as BuilderComponent;
	posthog.capture("builder_component_created", { component_name: componentData.name });
	componentStore.setComponentMap(componentData);
	const block = store.activeCanvas?.findBlock(props.block.blockId);
	if (!block) return;
	block.extendFromComponent(componentData.name);
	componentName.value = "";
	isGlobalComponent.value = 0;
	context.close();
};
</script>
