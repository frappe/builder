<template>
	<div class="editor group relative cursor-pointer"
		:class="{ 'border-2 border-blue-400': store.selected_component && store.selected_component.element_id === elementProperties.id }">
		<component v-if="elementProperties.node_type !== 'Text'" :is="elementProperties.element"
			class="flex items-center justify-center relative component"
			@click.exact.stop="select_component($event, elementProperties)" @dblclick.stop draggable="true"
			v-bind="{ ...elementProperties.attributes, ...elementProperties.skipped_attributes }"
			:style="elementProperties.styles" ref="component">
			{{ elementProperties.innerText }}
			<draggable :list="elementProperties.blocks" v-if="elementProperties.element === 'section'"
				:group="{ name: 'blocks' }" item-key="id" class="w-full h-full flex-col flex block-container">
				<template #item="{ element }">
					<Editable :element-properties="element"></Editable>
				</template>
			</draggable>
		</component>
		{{ elementProperties.node_type === 'Text' ? elementProperties.node_value : null }}
		<div class="absolute top-1 right-2 rounded-tr-md h-5 w-5 p-1 hidden group-hover:block">
			<FeatherIcon name="trash-2" class="text-gray-900 w-4 cursor-pointer" @click="remove" />
		</div>
	</div>
</template>
<script setup>
import { onMounted, ref } from 'vue';
import draggable from 'vuedraggable';
import { useStore } from '../store';
import Editable from './Editable.vue';

const component = ref(null);
const store = useStore();
const props = defineProps(['element-properties']);

// TODO: remove this
onMounted(() => {
	store.selected_component = component.value;
	store.selected_component.element_id = props.elementProperties.id;
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
