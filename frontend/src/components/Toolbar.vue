<template>
	<div class="toolbar bg-gray-300 p-2 flex justify-center h-14 shadow-sm" ref="toolbar">
		<input type="text" v-model="store.route"
			class="border-none rounded m-1 absolute left-4 h-8 bg-gray-200 text-base focus:ring-gray-400"
			placeholder="Page Name">
		<div class="breakpoint-options">
			<Button v-for="(option, device_name) in store.device_breakpoints"
				:active="store.active_breakpoint === option.device" appearance="minimal"
				@click="activate_breakpoint(option.device)" class="m-1">
				<FeatherIcon :name="option.icon" class="h-5 w-5 text-gray-700"></FeatherIcon>
			</Button>
		</div>
		<Button appearance="primary" @click="publish" class="m-1 absolute right-2 text-sm">Publish</Button>
	</div>
</template>
<script setup>
import { ref } from 'vue';
import { useStore } from "../store";
import { createResource } from 'frappe-ui';

const store = useStore();
const toolbar = ref(null);

const activate_breakpoint = (device) => {
	store.active_breakpoint = device;
}

let publish_web = createResource({
	url: 'website_builder.api.publish',
	onSuccess(page) {
		// hack
		page.options = JSON.parse(page.options);
		store.pages[page.name] = page;
		window.open("/" + page.route, '_blank');
	},
})

const publish = () => {
	console.log(toolbar);
	const a = document.createElement("a");
	var file = new Blob([toolbar.value.innerHTML], { type: "text/html" });
	a.href = URL.createObjectURL(file);
	// a.download = "published_file.html";
	publish_web.submit({ data: store.get_page_data(), route: store.route, page_name: store.page_name });
	// a.click();
}

</script>