<template>
	<div class="bg-gray-200 w-1/5 relative p-5 pr-2 z-20">
		<div v-if="store.selectedComponent">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Alignment</h3>
			<ul class="flex flex-wrap">
				<li v-for="alignment in store.alignments" :key="alignment.name" class="mr-2 mb-2 last:mr-0">
					<a @click="setAlignment(alignment)" class="hover:underline cursor-pointer text-base">
						<div class="w-8 h-8 rounded-md shadow-sm flex items-center justify-center bg-gray-100">
							<FeatherIcon :name="alignment.icon" class="w-4 h-4 text-gray-700"></FeatherIcon>
						</div>
					</a>
				</li>
			</ul>
		</div>
		<div v-if="store.selectedComponent" class="mt-5">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Background Color</h3>
			<ul class="flex flex-wrap">
				<li v-for="color in store.pastelCssColors" :key="color" class="mr-2 mb-2 last:mr-0">
					<a @click="setBgColor(color)" class="hover:underline cursor-pointer text-base">
						<div class="w-6 h-6 rounded-md shadow-sm" :style="'background-color:' + color"></div>
					</a>
				</li>
			</ul>
		</div>
		<div v-if="store.selectedComponent && store.selectedComponent.tagName !== 'IMG'" class="mt-5">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Text Color</h3>
			<ul class="flex flex-wrap">
				<li v-for="color in store.textColors" :key="color" class="mr-2 mb-2 last:mr-0">
					<a @click="setTextColor(color)" class="hover:underline cursor-pointer text-base">
						<div class="w-6 h-6 rounded-md shadow-sm" :style="'background-color:' + color"></div>
					</a>
				</li>
			</ul>
		</div>
		<div v-if="store.selectedComponent && store.selectedComponent.tagName === 'IMG'">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Image Source</h3>
			<input type="text" v-model="store.selectedComponent.src"
				class="w-full border-none border-gray-300 rounded-md text-sm h-8 focus:ring-gray-300">
		</div>
	</div>
</template>
<script setup>
import useStore from "../store";

const store = useStore();

const setBgColor = (color) => {
	store.selectedComponent.style.backgroundColor = color;
};
const setTextColor = (color) => {
	store.selectedComponent.style.color = color;
};

const setAlignment = (alignment) => {
	store.selectedComponent.classList.remove(
		...store.alignments.map((obj) => obj.class),
	);
	store.selectedComponent.classList.add(alignment.class);
};
</script>
