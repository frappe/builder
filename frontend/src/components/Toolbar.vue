<template>
	<div class="toolbar bg-gray-300 p-3 flex justify-center h-16" ref="toolbar">
		<div class="breakpoint-options">
			<Button v-for="(option, device_name) in store.device_breakpoints" :active="store.active_breakpoint === option.device" appearance="minimal" @click="activate_breakpoint(option.device)" class="m-1">
				<FeatherIcon :name="option.icon"  class="h-6 w-6 text-gray-700"></FeatherIcon>
			</Button>
		</div>
		<Button appearance="primary" @click="publish" class="m-1 absolute right-2">Publish</Button>
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
	onSuccess(route) {
		// hack
		window.open("/" + route, '_blank');
	},
})

const publish = () => {
	console.log(toolbar);
	const a = document.createElement("a");
	var file = new Blob([toolbar.value.innerHTML], {type: "text/html"});
	a.href = URL.createObjectURL(file);
	// a.download = "published_file.html";
	publish_web.submit({ data: store.get_page_data(), route: "/pages/hello-world" });
	// a.click();
}

</script>