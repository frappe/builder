<template>
	<div :style="{
		width: `${store.builderLayout.rightPanelWidth}px`
	}">
		<PanelResizer :width="store.builderLayout.rightPanelWidth" side="left"
			@resize="width => store.builderLayout.rightPanelWidth = width" max-width="400">
		</PanelResizer>
		<div v-if="store.canvasSelected">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Background Color</h3>
			<ul class="flex flex-wrap">
				<li v-for="color in store.pastelCssColors" :key="color" class="mr-2 mb-2 last:mr-0">
					<a @click="setCanvasBgColor(color)" class="hover:underline cursor-pointer text-base">
						<div class="w-6 h-6 rounded-md shadow-sm" :style="'background:' + color"></div>
					</a>
				</li>
			</ul>
			<Input :value="store.canvas.background" @change="color => setCanvasBgColor(color)" class="mt-2"></Input>
		</div>

		<div v-if="store.builderState.selectedBlock">
			<div>
				<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Alignment</h3>
				<ul class="flex flex-wrap">
					<li v-for="alignment in store.alignments" :key="alignment.name" class="mr-2 mb-2 last:mr-0">
						<a @click="setAlignment(alignment)" class="hover:underline cursor-pointer text-base">
							<div
								class="w-8 h-8 rounded-md shadow-sm flex items-center justify-center bg-gray-100 dark:bg-gray-800 dark:border-gray-700">
								<FeatherIcon :name="alignment.icon" class="w-4 h-4 text-gray-700 dark:text-gray-300">
								</FeatherIcon>
							</div>
						</a>
					</li>
					<li v-for="alignment in store.verticalAlignments" :key="alignment.name" class="mr-2 mb-2 last:mr-0">
						<a @click="setVerticalAlignment(alignment)" class="hover:underline cursor-pointer text-base">
							<div
								class="w-8 h-8 rounded-md shadow-sm flex items-center justify-center bg-gray-100 dark:bg-gray-800 dark:border-gray-700">
								<FeatherIcon :name="alignment.icon" class="w-4 h-4 text-gray-700 dark:text-gray-300">
								</FeatherIcon>
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
							<div
								class="w-8 h-8 rounded-md shadow-sm flex items-center justify-center bg-gray-100 dark:bg-gray-800 dark:border-gray-700">
								<FeatherIcon :name="flow.icon" class="w-4 h-4 text-gray-700 dark:text-gray-300">
								</FeatherIcon>
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

			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isImage()"
				:value="store.builderState.selectedBlock.attributes.src"
				@updateValue="val => store.builderState.selectedBlock.attributes.src = val">Image Source</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock.element" :value="store.builderState.selectedBlock.element"
				type="select" :options="['span', 'div', 'section', 'button', 'p', 'h1', 'h2', 'h3']"
				@updateValue="val => store.builderState.selectedBlock.element = val">Tag</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
				:value="blockStyles.fontSize" @updateValue="val => blockStyles.fontSize = val">Font Size</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
				:value="blockStyles.fontWeight" @updateValue="val => blockStyles.fontWeight = val">Font Weight</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
				:value="blockStyles.letterSpacing" @updateValue="val => blockStyles.letterSpacing = val">Letter Spacing
			</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isText()"
				:value="blockStyles.lineHeight" @updateValue="val => blockStyles.lineHeight = val">Line Height</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isContainer()"
				:value="blockStyles.margin" @updateValue="val => blockStyles.margin = val">Margin</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock" :value="blockStyles.height"
				@updateValue="val => blockStyles.height = val">Height</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock" :value="blockStyles.width"
				@updateValue="val => blockStyles.width = val">Width</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isLink()"
				:value="store.builderState.selectedBlock.attributes.href"
				@updateValue="val => store.builderState.selectedBlock.attributes.href = val">Link</InlineInput>
			<InlineInput v-if="store.builderState.selectedBlock && store.builderState.selectedBlock.isButton()"
				:value="store.builderState.selectedBlock.attributes.onclick"
				@updateValue="val => store.builderState.selectedBlock.attributes.onclick = val">Action</InlineInput>
		</div>
	</div>
</template>
<script setup>
import { computed } from "vue";
import { Input } from "frappe-ui";
import PanelResizer from "./PanelResizer.vue";
import InlineInput from "./InlineInput.vue";
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

const setCanvasBgColor = (color) => {
	store.canvas.background = color;
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
