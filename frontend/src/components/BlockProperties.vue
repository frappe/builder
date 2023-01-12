<template>
	<div class="bg-gray-200 w-1/5 z-10 relative p-5">
		<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase" v-if="store.selected_component">Background Color</h3>
		<ul class="flex flex-wrap" v-if="store.selected_component">
			<li v-for="color in pastel_css_colors" class="mr-2 mb-2 last:mr-0">
				<a @click="set_bg_color(color)" class="hover:underline cursor-pointer text-base">
					<div class="w-6 h-6 rounded-md shadow-sm" :style="'background-color:#'+color"></div>
				</a>
			</li>
		</ul>
		<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5" v-if="store.selected_component">Text Color</h3>
		<ul class="flex flex-wrap" v-if="store.selected_component">
			<li v-for="color in text_colors" class="mr-2 mb-2 last:mr-0">
				<a @click="set_text_color(color)" class="hover:underline cursor-pointer text-base">
					<div class="w-6 h-6 rounded-md shadow-sm" :style="'background-color:#'+color"></div>
				</a>
			</li>
		</ul>
	</div>
</template>
<script setup>
import { useStore } from "../store";
const store = useStore();
let pastel_css_colors = ["F5FFFA","F8F8FF","F0F8FF","F5F5DC","FFE4C4","FFEBCD","FFDEAD","FFC1C1","FFB6C1","FFA07A","FF8C00","FF7F50","FF69B4","FF6347","FDB813","FDAB9F","FDA50F","FCB4D5","FBB5A3","FBB917","FBB972","FBB9AC","FBCEB1","FBF9F9","FAFAD2","FAF0E6","F9EBE0","F9E79F","F49AC2","FFB347","FFD700","ADFF2F","87CEFA","00BFFF","ADD8E6","B0E0E6","5F9EA0","FDD5B1","FCCDE3","FCC2D9","FCB4D5","FBB5A3","FBB917","FBB972","FBB9AC","FBCEB1"];

let text_colors = ["000000", "424242", "636363", "9C9C94", "CEC6CE", "EFEFEF", "F7F7F7", "FFFFFF", "FF0000", "00FF00", "0000FF", "FFFF00", "00FFFF", "FF00FF", "C0C0C0", "808080", "808000", "008080", "800080", "800000"];

const set_bg_color = (color) => {
	store.selected_component.style.backgroundColor = "#" + color;
}
const set_text_color = (color) => {
	store.selected_component.style.color = "#" + color;
}
</script>