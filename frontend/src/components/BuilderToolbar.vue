<template>
	<div class="toolbar bg-gray-300 p-2 flex justify-center h-14 shadow-sm" ref="toolbar">
		<input type="text" v-model="store.route"
			class="border-none rounded m-1 absolute left-4 h-8 bg-gray-200 text-base focus:ring-gray-400"
			placeholder="Page Name">
		<div class="breakpoint-options">
			<Button v-for="(option, deviceName) in store.device_breakpoints"
				:key="deviceName"
				:active="store.active_breakpoint === option.device" appearance="minimal"
				@click="activateBreakpoint(option.device)" class="m-1">
				<FeatherIcon :name="option.icon" class="h-5 w-5 text-gray-700"></FeatherIcon>
			</Button>
		</div>
		<Button appearance="primary" @click="publish" class="m-1 absolute right-2 text-sm">
			Publish
		</Button>
	</div>
</template>
<script setup>
import { ref } from "vue";
import { createResource } from "frappe-ui";
import useStore from "../store";

const store = useStore();
const toolbar = ref(null);

const activateBreakpoint = (device) => {
	store.active_breakpoint = device;
};

const publishWebResource = createResource({
	url: "website_builder.api.publish",
	onSuccess(page) {
		// hack
		page.options = JSON.parse(page.options);
		store.pages[page.name] = page;
		window.open(`/${page.route}`, "_blank");
	},
});

const publish = () => {
	const a = document.createElement("a");
	const file = new Blob([toolbar.value.innerHTML], { type: "text/html" });
	a.href = URL.createObjectURL(file);
	// a.download = "published_file.html";
	publishWebResource.submit({
		data: store.getPageData(),
		route: store.route,
		page_name: store.page_name,
	});
	// a.click();
};

</script>
