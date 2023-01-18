<template>
	<div class="bg-gray-200 w-1/5 relative p-5 pr-2 z-20">
		<div v-if="store.selected_component">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Alignment</h3>
			<ul class="flex flex-wrap">
				<li v-for="alignment in store.alignments" class="mr-2 mb-2 last:mr-0">
					<a @click="set_alignment(alignment)" class="hover:underline cursor-pointer text-base">
						<div class="w-8 h-8 rounded-md shadow-sm flex items-center justify-center bg-gray-100">
							<FeatherIcon :name="alignment.icon" class="w-4 h-4 text-gray-700"></FeatherIcon>
						</div>
					</a>
				</li>
			</ul>
		</div>
		<div v-if="store.selected_component" class="mt-5">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Background Color</h3>
			<ul class="flex flex-wrap">
				<li v-for="color in store.pastel_css_colors" class="mr-2 mb-2 last:mr-0">
					<a @click="set_bg_color(color)" class="hover:underline cursor-pointer text-base">
						<div class="w-6 h-6 rounded-md shadow-sm" :style="'background-color:' + color"></div>
					</a>
				</li>
			</ul>
		</div>
		<div v-if="store.selected_component && store.selected_component.tagName !== 'IMG'" class="mt-5">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Text Color</h3>
			<ul class="flex flex-wrap">
				<li v-for="color in store.text_colors" class="mr-2 mb-2 last:mr-0">
					<a @click="set_text_color(color)" class="hover:underline cursor-pointer text-base">
						<div class="w-6 h-6 rounded-md shadow-sm" :style="'background-color:' + color"></div>
					</a>
				</li>
			</ul>
		</div>
		<div v-if="store.selected_component && store.selected_component.tagName === 'IMG'">
			<!--show option to set img src--->
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Image Source</h3>
			<input type="text" v-model="store.selected_component.src"
				class="w-full border-none border-gray-300 rounded-md text-sm h-8 focus:ring-gray-300">
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

const set_alignment = (alignment) => {
	store.selected_component.classList.remove(...store.alignments.map(alignment => alignment.class));
	store.selected_component.classList.add(alignment.class);
}
</script>