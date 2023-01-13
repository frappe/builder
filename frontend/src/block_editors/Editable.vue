<template>
	<div class="editor group relative hover:border-2 hover:border-blue-400 cursor-pointer">
		<component v-if="elementProperties.node_type !== 'Text'" :is="elementProperties.element"
			class="flex items-center justify-center relative component"
			@click.stop="select_component"
			@dblclick.stop
			draggable="true" v-bind="{...elementProperties.attributes, ...elementProperties.skipped_attributes}" :style="elementProperties.styles">
			{{elementProperties.innerText}}
			<draggable :list="elementProperties.blocks" v-if="elementProperties.element === 'section'" :group="{ name: 'blocks' }" item-key="id"
				class="w-full h-full flex-col flex block-container">
				<template #item="{ element }">
					<Editable :element-properties="element"></Editable>
				</template>
			</draggable>
		</component>
		{{ elementProperties.node_type === 'Text' ? elementProperties.node_value: null}}
		<div class="absolute top-1 right-2 rounded-tr-md h-5 w-5 p-1 hidden group-hover:block">
			<FeatherIcon name="trash-2" class="text-gray-900 w-4 cursor-pointer" @click="remove" />
		</div>
	</div>
</template>
<script setup>
import draggable from 'vuedraggable';
import Editable from './Editable.vue';
import { FeatherIcon } from 'frappe-ui';
import { useStore } from '../store';

const store = useStore();
defineProps(['element-properties']);
const remove = (e) => {
	e.target.closest(".editor").remove();
}
const select_component = (e) => {
	store.selected_component = e.target.closest(".component");
}
</script>
