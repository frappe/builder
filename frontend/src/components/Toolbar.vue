<template>
	<div class="toolbar bg-gray-300 p-4 flex justify-between" ref="toolbar">
		<span class="font-bold uppercase font-lg pt-2">Web Buddy</span>
		<div class="breakpoint-options">
			<Button v-for="option in breakpoint_options" :active="store.active_breakpoint === option.device" appearance="minimal">
				<FeatherIcon :name="option.icon"  class="h-6 w-6"></FeatherIcon>
			</Button>
		</div>
		<Button appearance="primary" @click="publish" class="uppercase">Publish</Button>
	</div>
</template>
<script setup>
import { ref } from 'vue';
import { useStore } from "../store";
const store = useStore();
const toolbar = ref(null);

const publish = () => {
	console.log(toolbar);
	const a = document.createElement("a");
	var file = new Blob([toolbar.value.innerHTML], {type: "text/html"});
	a.href = URL.createObjectURL(file);
	// a.download = "published_file.html";
	a.click();
}

let breakpoint_options = [
	{
		"icon": "monitor",
		"device": "desktop",
		"width": 1024,
		"active": true
	},
	{
		"icon": "smartphone",
		"device": "mobile",
		"width": 320,
		"active": false
	}, {
		"icon": "tablet",
		"device": "tablet",
		"width": 640,
		"active": false
	}
]

</script>