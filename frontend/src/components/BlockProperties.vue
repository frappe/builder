<template>
	<div>
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
				<li v-for="alignment in store.verticalAlignments" :key="alignment.name" class="mr-2 mb-2 last:mr-0">
					<a @click="setVerticalAlignment(alignment)" class="hover:underline cursor-pointer text-base">
						<div class="w-8 h-8 rounded-md shadow-sm flex items-center justify-center bg-gray-100">
							<FeatherIcon :name="alignment.icon" class="w-4 h-4 text-gray-700"></FeatherIcon>
						</div>
					</a>
				</li>
			</ul>
		</div>
		<div v-if="store.selectedComponent" class="mt-5">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Flow</h3>
			<ul class="flex flex-wrap">
				<li v-for="flow in store.flow" :key="flow.name" class="mr-2 mb-2 last:mr-0">
					<a @click="setFlow(flow)" class="hover:underline cursor-pointer text-base">
						<div class="w-8 h-8 rounded-md shadow-sm flex items-center justify-center bg-gray-100">
							<FeatherIcon :name="flow.icon" class="w-4 h-4 text-gray-700"></FeatherIcon>
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
						<div class="w-6 h-6 rounded-md shadow-sm" :style="'background:' + color"></div>
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
				class="w-full border-none border-gray-300 rounded-md text-sm h-8 focus:ring-gray-300 bg-gray-100">
		</div>
		<div v-if="store.selectedComponent && store.selectedComponent.tagName === 'SPAN'">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Font Size</h3>
			<input type="text" v-model="fontSize" class="w-full border-none border-gray-300 rounded-md text-sm h-8 focus:ring-gray-300 bg-gray-100">
		</div>

		<div v-if="store.selectedComponent && store.selectedComponent.tagName === 'SPAN'">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Line Height</h3>
			<input type="text" v-model="lineHeight" class="w-full border-none border-gray-300 rounded-md text-sm h-8 focus:ring-gray-300 bg-gray-100">
		</div>

		<div v-if="store.selectedComponent && store.selectedComponent.tagName === 'SECTION'">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Margin</h3>
			<input type="text" v-model="margin"
				class="w-full border-none border-gray-300 rounded-md text-sm h-8 focus:ring-gray-300 bg-gray-100">
		</div>
		<div v-if="store.selectedComponent" class="text-base mt-5 text-gray-800">
			Width: {{ width }}
			height: {{ height }}
		</div>
	</div>
</template>
<script setup>
import { computed } from "@vue/reactivity";
import { Input } from "frappe-ui";
import useStore from "../store";
const store = useStore();

let margin = computed({
	get: () => store.selectedComponent.style.margin,
	set: (val) => {
		store.selectedComponent.style.margin = val;
	}
})
let fontSize = computed({
	get: () => store.selectedComponent.style.fontSize,
	set: (val) => {
		store.selectedComponent.style.fontSize = val;
	}
})

let lineHeight = computed({
	get: () => store.selectedComponent.style.lineHeight,
	set: (val) => {
		store.selectedComponent.style.lineHeight = val;
	}
})

let height = computed({
	get: () => store.selectedComponent.style.height || "auto",
	set: (val) => {
		store.selectedComponent.style.lineHeight = val;
	}
})

let width = computed({
	get: () => store.selectedComponent.style.width || "auto",
	set: (val) => {
		store.selectedComponent.style.lineHeight = val;
	}
})

const setBgColor = (color) => {
	store.selectedComponent.style.background = color;
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

const setVerticalAlignment = (alignment) => {
	store.selectedComponent.classList.remove(
		...store.verticalAlignments.map((obj) => obj.class),
	);
	store.selectedComponent.classList.add(alignment.class);
};
const setFlow = (flow) => {
	store.selectedComponent.classList.remove(
		...store.flow.map((obj) => obj.class),
	);
	store.selectedComponent.classList.add(flow.class);
};
</script>
