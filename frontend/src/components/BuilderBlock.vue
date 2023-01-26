<template>
	<component v-if="elementProperties.node_type !== 'Text'" :is="elementProperties.element"
		class="flex items-center justify-center relative __builder_component__ mx-auto"
		@click.exact.stop="selectComponent($event, elementProperties)" @dblclick.stop draggable="true"
		v-bind="{ ...elementProperties.attributes, ...elementProperties.skipped_attributes }"
		:style="elementProperties.styles" ref="component">
		{{ elementProperties.innerText }}
		<draggable :list="elementProperties.blocks" v-if="elementProperties.element === 'section'"
			:group="{ name: 'blocks' }" item-key="id" class="w-full h-full flex-col flex block-container">
			<template #item="{ element }">
				<BuilderBlock :element-properties="element"></BuilderBlock>
			</template>
		</draggable>
	</component>
	<teleport to='#overlay'>
		<BlockEditor :movable="elementProperties.element === 'span'"></BlockEditor>
	</teleport>
</template>
<script setup>
import { onMounted, ref } from "vue";
import draggable from "vuedraggable";
import useStore from "../store";
import BlockEditor from "./BlockEditor.vue";

const component = ref(null);
const store = useStore();
const props = defineProps(["element-properties"]);

onMounted(() => {
	store.selectedComponent = component.value;
	store.selectedComponent.element_id = props.elementProperties.id;
});

const selectComponent = (e, elementProperties) => {
	store.selectedComponent = e.target.closest(".__builder_component__");
	store.selectedComponent.element_id = elementProperties.id;
};

</script>
