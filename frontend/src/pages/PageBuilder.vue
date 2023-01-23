<template>
	<div class="flex-col bg-gray-100">
		<BuilderToolbar class="z-30 relative"></BuilderToolbar>
		<div class="flex justify-center">
			<BuilderSidebar></BuilderSidebar>
			<BuilderCanvas></BuilderCanvas>
			<BlockProperties></BlockProperties>
		</div>
	</div>
</template>

<script setup>
import BuilderCanvas from "../components/BuilderCanvas.vue";
import BuilderToolbar from "../components/BuilderToolbar.vue";
import BuilderSidebar from "../components/BuilderSidebar.vue";
import BlockProperties from "../components/BlockProperties.vue";

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
