<template>
	<div class="bg-gray-200 w-1/5 z-10 relative p-5">
		<div  v-if="store.selected_component">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Background Color</h3>
			<ul class="flex flex-wrap">
				<li v-for="color in store.pastel_css_colors" class="mr-2 mb-2 last:mr-0">
					<a @click="set_bg_color(color)" class="hover:underline cursor-pointer text-base">
						<div class="w-6 h-6 rounded-md shadow-sm" :style="'background-color:'+color"></div>
					</a>
				</li>
			</ul>
		</div>
		<div v-if="store.selected_component">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5" >Text Color</h3>
			<ul class="flex flex-wrap">
				<li v-for="color in store.text_colors" class="mr-2 mb-2 last:mr-0">
					<a @click="set_text_color(color)" class="hover:underline cursor-pointer text-base">
						<div class="w-6 h-6 rounded-md shadow-sm" :style="'background-color:'+color"></div>
					</a>
				</li>
			</ul>
		</div>
		<div v-if="store.selected_component && store.selected_component.tagName === 'IMG'">
			<!--show option to set img src--->
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5" >Image Source</h3>
			<input type="text" v-model="store.selected_component.src" class="w-full border-none border-gray-300 rounded-md">
		</div>
	</div>
</template>
<script setup>
import { useStore } from "../store";
const store = useStore();

const set_bg_color = (color) => {
	store.selected_component.style.backgroundColor = color;
}
const set_text_color = (color) => {
	store.selected_component.style.color = color;
}
</script>