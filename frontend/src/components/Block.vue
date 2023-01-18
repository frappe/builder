<template>
	<component v-if="elementProperties.node_type !== 'Text'" :is="elementProperties.element"
		class="flex items-center justify-center relative component"
		@click.exact.stop="select_component($event, elementProperties)" @dblclick.stop draggable="true"
		v-bind="{ ...elementProperties.attributes, ...elementProperties.skipped_attributes }"
		:style="elementProperties.styles" ref="component">
		{{ elementProperties.innerText }}
		<draggable :list="elementProperties.blocks" v-if="elementProperties.element === 'section'"
			:group="{ name: 'blocks' }" item-key="id" class="w-full h-full flex-col flex block-container">
			<template #item="{ element }">
				<Block :element-properties="element"></Block>
			</template>
		</draggable>
	</component>
</template>
<script setup>
import { onMounted, ref } from 'vue';
import draggable from 'vuedraggable';
import { useStore } from '../store';
import set_resizer from '../utils/resizer';
import Block from './Block.vue';


const component = ref(null);
const store = useStore();
const props = defineProps(['element-properties']);

onMounted(() => {
	store.selected_component = component.value;
	store.selected_component.element_id = props.elementProperties.id;
	set_resizer(component.value);
})

const remove = (e) => {
	e.target.closest(".editor").remove();
}

const copy_element = (e) => {
	console.log('copying element', e);
}

const select_component = (e, element_properties) => {
	store.selected_component = e.target.closest(".component");
	store.selected_component.element_id = element_properties.id;
}

</script>
