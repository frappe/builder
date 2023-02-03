<template>
	<div class="toolbar bg-white p-2 flex justify-center h-14 shadow-sm" ref="toolbar">
		<input type="text" v-model="store.route"
			class="border-none rounded m-1 absolute left-4 h-8 bg-gray-100 text-base focus:ring-gray-400"
			placeholder="Page Name">
		<div class="breakpoint-options">
			<Button v-for="(option, deviceName) in store.deviceBreakpoints"
				:key="deviceName"
				:active="store.activeBreakpoint === option.device" appearance="minimal"
				@click="activateBreakpoint(option.device)" class="m-1">
				<FeatherIcon :name="option.icon" class="h-5 w-5 text-gray-800"></FeatherIcon>
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
	store.activeBreakpoint = device;
};

const publishWebResource = createResource({
	url: "website_builder.api.publish",
	onSuccess(page) {
		// hack
		page.blocks = JSON.parse(page.blocks);
		store.pages[page.name] = page;
		window.open(`/${page.route}`, "_blank");
	},
});

const publish = () => {
	publishWebResource.submit({
		blocks: store.getPageData(),
		route: store.route,
		page_name: store.pageName,
	});
};

</script>
