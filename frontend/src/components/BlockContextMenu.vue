<template>
	<div>
		<ContextMenu ref="contextMenu" :options="contextMenuOptions" :context="menuContext" />
		<NewBlockTemplate
			v-if="menuContext"
			:block="menuContext.block"
			v-model="builderStore.showBlockTemplateDialog"></NewBlockTemplate>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import { blockContextMenuOptions } from "@/components/BlockContextMenuOptions";
import ContextMenu from "@/components/ContextMenu.vue";
import NewBlockTemplate from "@/components/Modals/NewBlockTemplate.vue";
import useBuilderStore from "@/stores/builderStore";
import type { BlockMenuContext } from "@/types/blockContextMenu";
import { Ref, ref } from "vue";

const builderStore = useBuilderStore();

// read all, not visible: each item applies its own condition to the context
const contextMenuOptions = blockContextMenuOptions.all;

const contextMenu = ref(null) as unknown as Ref<InstanceType<typeof ContextMenu>>;
const menuContext = ref(null) as unknown as Ref<BlockMenuContext>;

const showContextMenu = (event: MouseEvent, refBlock: Block) => {
	const target = event.target as HTMLElement;
	menuContext.value = {
		block: refBlock,
		target,
		fromLayersPanel: Boolean(target.closest(".block-layers")),
	};
	if (refBlock.isRoot()) return;
	contextMenu.value?.show(event);
};

defineExpose({
	showContextMenu,
});
</script>
