<template>
	<div class="toolbar bg-gray-300 p-4 flex justify-between">
		<span>Web Buddy</span>
		<div class="breakpoint-options">
			<Button v-for="option in breakpoint_options" :active="store.active_breakpoint === option.device" appearance="minimal">
				<FeatherIcon :name="option.icon"  class="h-6 w-6"></FeatherIcon>
			</Button>
		</div>
		<Button appearance="primary" @click="publish">Publish</Button>
	</div>
</template>
<script setup>
import {useStore} from "../store";
const store = useStore();

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
let publish = () => {
	console.log('publish');
}
</script>