<template>
	<div class="toolbar bg-white p-2 flex justify-center h-14 shadow-sm" ref="toolbar">
		<input type="text" v-model="store.pageName"
			class="border-none rounded m-1 absolute left-4 h-8 bg-gray-100 dark:bg-gray-800 text-base focus:ring-gray-400 dark:focus:ring-gray-700 dark:text-gray-300"
			placeholder="Page Name">
		<div class="breakpoint-options">
			<Button v-for="(option, deviceName) in store.deviceBreakpoints"
				:key="deviceName"
				:class="{
					'bg-gray-200 dark:bg-gray-700': store.activeBreakpoint === option.device,
					'text-gray-700 dark:text-gray-400': store.activeBreakpoint !== option.device,
					'dark:focus:bg-gray-700 dark:hover:bg-gray-800': true
				}"
				:active="store.activeBreakpoint === option.device" appearance="minimal"
				@click="activateBreakpoint(option.device)" class="m-1">
				<FeatherIcon :name="option.icon" class="h-5 w-5 text-gray-800 dark:text-gray-400"></FeatherIcon>
			</Button>
		</div>
		<Button appearance="default" @click="publish" class="m-1 absolute right-2 text-sm p-4 border-gray-500">
			<FeatherIcon name="play" class="w-3 h-4 text-zinc-900 dark:text-gray-50"></FeatherIcon>
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
		store.pageName = page.page_name;
		window.open(`/${page.route}`, "_blank");
	},
});

const publish = () => {
	publishWebResource.submit({
		blocks: store.getPageData(),
		page_name: store.pageName,
	});
};

</script>
