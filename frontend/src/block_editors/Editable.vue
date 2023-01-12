<template>
	<div class="editor group relative hover:border-2 hover:border-blue-400">
		<component :is="elementProperties.element"
			class="flex items-center cursor-pointer justify-center overflow-auto group-hover:border-2 group-hover:border-blue-200 relative component"
			@click="select_component"
			draggable="true" v-bind="{...elementProperties.attributes, ...elementProperties.skipped_attributes}" :style="elementProperties.styles"> {{
				elementProperties.innerText
			}}
		</component>
		<div class="absolute top-1 right-2 rounded-tr-md h-5 w-5 p-1 hidden group-hover:block">
			<FeatherIcon name="trash-2" class="text-gray-900 w-4 cursor-pointer" @click="remove" />
		</div>
	</div>
</template>
<script setup>
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
