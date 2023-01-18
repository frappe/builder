<template>
	<div class="flex-col bg-gray-100">
		<Toolbar class="z-30 relative"></Toolbar>
		<div class="flex justify-center">
			<Sidebar></Sidebar>
			<Canvas></Canvas>
			<BlockProperties></BlockProperties>
		</div>
	</div>
</template>

<script setup>
import Canvas from '../components/Canvas.vue';
import Toolbar from '../components/Toolbar.vue';
import Sidebar from '../components/Sidebar.vue';
import BlockProperties from '../components/BlockProperties.vue';

import { useStore } from "../store";

const store = useStore();
// const webpages = createResource({
// 	url: "frappe.client.get_list",
// 	onSuccess(data) {
// 		console.log(data);
// 	}
// });

// webpages.submit({
// 	doctype: "Web Page Beta",
// 	fields: ["name", "title", "route", "options"],
// });

</script>