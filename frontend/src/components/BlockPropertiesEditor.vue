<template>
	<div :style="{
		width: `${store.builderLayout.rightPanelWidth}px`
	}">
		<PanelResizer :width="store.builderLayout.rightPanelWidth" side="left"
			@resize="width => store.builderLayout.rightPanelWidth = width"
			max-width="400">
		</PanelResizer>
		<div v-if="store.builderState.selectedBlock">
			<div>
				<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Alignment</h3>
				<ul class="flex flex-wrap">
					<li v-for="alignment in store.alignments" :key="alignment.name" class="mr-2 mb-2 last:mr-0">
						<a @click="setAlignment(alignment)" class="hover:underline cursor-pointer text-base">
							<div class="w-8 h-8 rounded-md shadow-sm flex items-center justify-center bg-gray-100 dark:bg-gray-800 dark:border-gray-700">
								<FeatherIcon :name="alignment.icon" class="w-4 h-4 text-gray-700 dark:text-gray-300"></FeatherIcon>
							</div>
						</a>
					</li>
					<li v-for="alignment in store.verticalAlignments" :key="alignment.name" class="mr-2 mb-2 last:mr-0">
						<a @click="setVerticalAlignment(alignment)" class="hover:underline cursor-pointer text-base">
							<div class="w-8 h-8 rounded-md shadow-sm flex items-center justify-center bg-gray-100 dark:bg-gray-800 dark:border-gray-700">
								<FeatherIcon :name="alignment.icon" class="w-4 h-4 text-gray-700 dark:text-gray-300"></FeatherIcon>
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
							<div class="w-8 h-8 rounded-md shadow-sm flex items-center justify-center bg-gray-100 dark:bg-gray-800 dark:border-gray-700">
								<FeatherIcon :name="flow.icon" class="w-4 h-4 text-gray-700 dark:text-gray-300"></FeatherIcon>
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
			<div v-if="store.builderState.selectedBlock && !store.builderState.selectedBlock.isImage()" class="mt-5">
				<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Text Color</h3>
				<ul class="flex flex-wrap">
					<li v-for="color in store.textColors" :key="color" class="mr-2 mb-2 last:mr-0">
						<a @click="setTextColor(color)" class="hover:underline cursor-pointer text-base">
							<div class="w-6 h-6 rounded-md shadow-sm" :style="'background-color:' + color"></div>
						</a>
					</li>
				</ul>
			</div>
			<div v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isImage()">
				<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Image Source</h3>
				<input type="text" v-model="store.builderState.selectedBlock.attributes.src"
					class="w-full border-none border-gray-300 rounded-md text-sm h-8 bg-gray-100 dark:bg-gray-800 focus:ring-gray-400 dark:focus:ring-gray-700 dark:text-gray-300">
			</div>
			<div v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()">
				<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Font Size</h3>
				<input type="text" v-model="blockStyles.fontSize" class="w-full border-none border-gray-300 rounded-md text-sm h-8 bg-gray-100 dark:bg-gray-800 focus:ring-gray-400 dark:focus:ring-gray-700 dark:text-gray-300">
			</div>

			<div>
				<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Tag</h3>
				<Input type="select" :options="['span', 'div', 'section', 'button', 'p', 'h1', 'h2', 'h3']" v-model="store.builderState.selectedBlock.element" class="bg-gray-100 dark:bg-gray-800 text-base focus:ring-gray-400 dark:focus:ring-gray-700 dark:text-gray-300"/>
			</div>

			<div v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()">
				<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Line Height</h3>
				<input type="text" v-model="blockStyles.lineHeight" class="w-full border-none border-gray-300 rounded-md text-sm h-8 bg-gray-100 dark:bg-gray-800 focus:ring-gray-400 dark:focus:ring-gray-700 dark:text-gray-300">
			</div>

			<div v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer()">
				<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Margin</h3>
				<input type="text" v-model="blockStyles.margin"
					class="w-full border-none border-gray-300 rounded-md text-sm h-8 bg-gray-100 dark:bg-gray-800 focus:ring-gray-400 dark:focus:ring-gray-700 dark:text-gray-300">
			</div>
			<div v-if="store.builderState.selectedBlock">
				<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Element Type</h3>
				<input type="text" v-model="store.builderState.selectedBlock.element"
					class="w-full border-none border-gray-300 rounded-md text-sm h-8 bg-gray-100 dark:bg-gray-800 focus:ring-gray-400 dark:focus:ring-gray-700 dark:text-gray-300">
			</div>
			<div v-if="store.builderState.selectedBlock">
				<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Height</h3>
				<Input v-model="blockStyles.height" type="text" class="bg-gray-100 dark:bg-gray-800 text-base focus:ring-gray-400 dark:focus:ring-gray-700 dark:text-gray-300"/>
			</div>
			<div v-if="store.builderState.selectedBlock">
				<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Width</h3>
				<input type="text" v-model="blockStyles.width"
					class="w-full border-none border-gray-300 rounded-md text-sm h-8 bg-gray-100 dark:bg-gray-800 focus:ring-gray-400 dark:focus:ring-gray-700 dark:text-gray-300">
			</div>
			<div v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isLink()">
				<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Link</h3>
				<input type="text" v-model="store.builderState.selectedBlock.attributes.href"
					class="w-full border-none border-gray-300 rounded-md text-sm h-8 bg-gray-100 dark:bg-gray-800 focus:ring-gray-400 dark:focus:ring-gray-700 dark:text-gray-300">
			</div>
			<div v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isButton()">
				<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mt-5">Action</h3>
				<Input type="textarea" v-model="store.builderState.selectedBlock.attributes.onclick"/>
			</div>
		</div>
	</div>
</template>
<script setup>
import { computed } from "vue";
import { Input } from "frappe-ui";
import PanelResizer from "./PanelResizer.vue";
import useStore from "../store";
const store = useStore();

const blockStyles = computed(() => {
	let styleObj = store.builderState.selectedBlock.styles;
	if (store.builderState.activeBreakpoint === 'mobile') {
		styleObj = store.builderState.selectedBlock.mobileStyles;
	} else if (store.builderState.activeBreakpoint === 'tablet') {
		styleObj = store.builderState.selectedBlock.tabletStyles;
	}
	return styleObj;
})

const setBgColor = (color) => {
	store.builderState.selectedBlock.setStyle('background', color);
};
const setTextColor = (color) => {
	store.builderState.selectedBlock.setStyle('color', color);
};

const setAlignment = (alignment) => {
	store.builderState.selectedBlock.setStyle(alignment.styleKey, alignment.styleValue);
};

const setVerticalAlignment = (alignment) => {
	store.builderState.selectedBlock.setStyle(alignment.styleKey, alignment.styleValue);
};
const setFlow = (flow) => {
	store.builderState.selectedBlock.setStyle(flow.styleKey, flow.styleValue);
};
</script>
