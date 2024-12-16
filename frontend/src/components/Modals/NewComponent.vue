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
			<BuilderInput type="text" v-model="componentProperties.componentName" label="Component Name" required />
			<div class="mt-3">
				<BuilderInput
					class="text-sm [&>span]:!text-sm"
					type="checkbox"
					v-model="componentProperties.isGlobalComponent"
					label="Global Component" />
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import webComponent from "@/data/webComponent";
import useStore from "@/store";
import { posthog } from "@/telemetry";
import { BuilderComponent } from "@/types/Builder/BuilderComponent";
import Block from "@/utils/block";
import { getBlockCopy, getBlockInstance, getBlockString } from "@/utils/helpers";
import { ref } from "vue";

const store = useStore();

const props = defineProps<{
	block: Block;
}>();

const componentProperties = ref({
	componentName: "",
	isGlobalComponent: 0,
});

const createComponentHandler = (close: () => void) => {
	const blockCopy = getBlockCopy(props.block, true);
	blockCopy.removeStyle("left");
	blockCopy.removeStyle("top");
	blockCopy.removeStyle("position");
	webComponent.insert
		.submit({
			block: getBlockString(blockCopy),
			component_name: componentProperties.value.componentName,
			for_web_page: componentProperties.value.isGlobalComponent ? null : store.selectedPage,
		})
		.then(async (data: BuilderComponent) => {
			posthog.capture("builder_component_created", { component_name: data.name });
			store.componentMap.set(data.name, getBlockInstance(data.block));
			const block = store.activeCanvas?.findBlock(props.block.blockId);
			if (!block) return;
			block.extendFromComponent(data.name);
		});
	close();
};
</script>
