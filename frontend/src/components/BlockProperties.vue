<template>
	<div v-if="store.selectedBlock">
		<div>
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
		<div class="mt-5">
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
		<div class="mt-5">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Background Color</h3>
			<ul class="flex flex-wrap">
				<li v-for="color in store.pastelCssColors" :key="color" class="mr-2 mb-2 last:mr-0">
					<a @click="setBgColor(color)" class="hover:underline cursor-pointer text-base">
						<div class="w-6 h-6 rounded-md shadow-sm" :style="'background:' + color"></div>
					</a>
				</li>
			</ul>
		</div>
		<div v-if="store.selectedBlock && !store.selectedBlock.isImage()" class="mt-5">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Text Color</h3>
			<ul class="flex flex-wrap">
				<li v-for="color in store.textColors" :key="color" class="mr-2 mb-2 last:mr-0">
					<a @click="setTextColor(color)" class="hover:underline cursor-pointer text-base">
						<div class="w-6 h-6 rounded-md shadow-sm" :style="'background-color:' + color"></div>
					</a>
				</li>
			</ul>
		</div>
		<div v-if="store.selectedBlock && store.selectedBlock.isImage()">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Image Source</h3>
			<input type="text" v-model="store.selectedBlock.attributes.src"
				class="w-full border-none border-gray-300 rounded-md text-sm h-8 focus:ring-gray-300 bg-gray-100">
		</div>
		<div v-if="store.selectedBlock && store.selectedBlock.isText()">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Font Size</h3>
			<input type="text" v-model="store.selectedBlock.styles.fontSize" class="w-full border-none border-gray-300 rounded-md text-sm h-8 focus:ring-gray-300 bg-gray-100">
		</div>

		<div v-if="store.selectedBlock && store.selectedBlock.isText()">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Line Height</h3>
			<input type="text" v-model="store.selectedBlock.styles.lineHeight" class="w-full border-none border-gray-300 rounded-md text-sm h-8 focus:ring-gray-300 bg-gray-100">
		</div>

		<div v-if="store.selectedBlock && store.selectedBlock.isContainer()">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Margin</h3>
			<input type="text" v-model="store.selectedBlock.styles.margin"
				class="w-full border-none border-gray-300 rounded-md text-sm h-8 focus:ring-gray-300 bg-gray-100">
		</div>
	</div>
</template>
<script setup>
import { computed } from "vue";
import { Input } from "frappe-ui";
import useStore from "../store";
const store = useStore();

const setBgColor = (color) => {
	store.selectedBlock.setStyle('background', color);
};
const setTextColor = (color) => {
	store.selectedBlock.setStyle('color', color);
};

const setAlignment = (alignment) => {
	store.selectedBlock.classes.remove(...store.alignments.map((obj) => obj.class),)
	store.selectedBlock.classes.add(alignment.class);
};

const setVerticalAlignment = (alignment) => {
	store.selectedBlock.classes.remove(...store.verticalAlignments.map((obj) => obj.class))
	store.selectedBlock.classes.add(alignment.class);
};
const setFlow = (flow) => {
	store.selectedBlock.classes.remove(...store.flow.map((obj) => obj.class))
	store.selectedBlock.classes.add(flow.class);
};
</script>
