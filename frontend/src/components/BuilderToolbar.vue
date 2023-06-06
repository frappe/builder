<template>
	<div class="toolbar flex h-14 items-center justify-center bg-white p-2 shadow-sm" ref="toolbar">
		<div class="absolute left-3 flex items-center">
			<router-link class="flex items-center" :to="{ name: 'home' }">
				<img src="/favicon.png" alt="logo" class="h-6" />
				<h1 class="ml-1 text-base text-gray-600 dark:text-gray-500">pages</h1>
			</router-link>
			<div class="ml-10 flex gap-3">
				<Button
					icon="mouse-pointer"
					appearance="minimal"
					class="!text-gray-700 dark:text-zinc-300 hover:dark:bg-slate-800 focus:dark:bg-slate-800 active:dark:bg-slate-700"
					@click="store.builderState.mode = 'select'"
					:active="store.builderState.mode === 'select'"></Button>
				<Button
					icon="type"
					appearance="minimal"
					class="!text-gray-700 dark:text-zinc-300 hover:dark:bg-slate-800 focus:dark:bg-slate-800 active:dark:bg-slate-700"
					@click="store.builderState.mode = 'text'"
					:active="store.builderState.mode === 'text'"></Button>
				<Button
					icon="square"
					appearance="minimal"
					class="!text-gray-700 dark:text-zinc-300 hover:dark:bg-slate-800 focus:dark:bg-slate-800 active:dark:bg-slate-700"
					@click="store.builderState.mode = 'container'"
					:active="store.builderState.mode === 'container'"></Button>
				<Button
					icon="image"
					appearance="minimal"
					class="!text-gray-700 dark:text-zinc-300 hover:dark:bg-slate-800 focus:dark:bg-slate-800 active:dark:bg-slate-700"
					@click="store.builderState.mode = 'image'"
					:active="store.builderState.mode === 'image'"></Button>
			</div>
		</div>
		<input
			type="text"
			v-model="store.pageName"
			class="h-7 rounded-md border-none bg-gray-100 text-base focus:ring-gray-400 dark:bg-zinc-800 dark:text-gray-300 dark:focus:ring-zinc-700"
			placeholder="Page Name" />
		<div class="absolute right-3 flex items-center">
			<router-link :to="{ name: 'page-settings' }">
				<FeatherIcon
					name="settings"
					class="mr-4 h-4 w-4 cursor-pointer text-gray-600 dark:text-gray-400"></FeatherIcon>
			</router-link>
			<UseDark v-slot="{ isDark, toggleDark }">
				<FeatherIcon
					:name="isDark ? 'moon' : 'sun'"
					class="mr-4 h-4 w-4 cursor-pointer text-gray-600 dark:text-gray-400"
					@click="toggleDark()" />
			</UseDark>
			<Button appearance="primary" @click="publish" class="rounded-2xl border-0 text-xs">Preview</Button>
		</div>
	</div>
</template>
<script setup lang="ts">
import { UseDark } from "@vueuse/components";
import { createResource } from "frappe-ui";
import { nextTick, ref, watch } from "vue";
import useStore from "../store";
import { clamp } from "@vueuse/core";
import { addPxToNumber, getRandomColor } from "@/utils/helpers";

const store = useStore();
const toolbar = ref(null);

const publishWebResource = createResource({
	url: "website_builder.api.publish",
	onSuccess(page: any) {
		// hack
		page.blocks = JSON.parse(page.blocks);
		store.pages[page.name] = page as Page;
		store.pageName = page.page_name;
		window.open(`/${page.route}`, "_blank");
	},
});

const publish = () => {
	publishWebResource.submit({
		blocks: store.getPageData(),
		page_name: store.pageName,
	});
};

watch(
	() => store.builderState.mode,
	() => {
		toggleMode(store.builderState.mode);
	}
);

const toggleMode = (mode: string) => {
	if (mode === "text") {
		const container = document.body.querySelector(".canvas-container") as HTMLElement;
		container.style.cursor = "text";

		const addText = (ev: MouseEvent) => {
			ev.preventDefault();
			let element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
			// check if element contains data-block-id
			if (element) {
				let block = store.builderState.blocks[0];
				if (element.dataset.blockId) {
					block = store.findBlock(element.dataset.blockId) || block;
				}
				const child = {
					name: "Text",
					element: "p",
					icon: "type",
					innerText: "Text",
					styles: {
						fontSize: "40px",
						width: "fit-content",
						"line-height": "1",
					} as BlockStyleMap,
				};

				const childBlock = block.addChild(child);
				childBlock.setStyle("position", "static");
				childBlock.setStyle("top", "auto");
				childBlock.setStyle("left", "auto");
				container.style.cursor = "auto";
				container.removeEventListener("mousedown", addText);
				setTimeout(() => {
					store.builderState.mode = "select";
				}, 50);
			}
			container.style.cursor = "auto";
			container.removeEventListener("mousedown", addText);
		};
		container.addEventListener("mousedown", addText);
	}

	if (mode === "container") {
		const container = document.body.querySelector(".canvas-container") as HTMLElement;
		container.style.cursor = "crosshair";

		const addContainer = (ev: MouseEvent) => {
			ev.preventDefault();
			ev.stopPropagation();
			let element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
			if (element) {
				let parentBlock = store.builderState.blocks[0];
				if (element.dataset.blockId) {
					parentBlock = store.findBlock(element.dataset.blockId) || parentBlock;
				}
				const child = {
					name: "Container",
					element: "div",
					icon: "square",
					styles: {
						width: "0px",
						height: "0px",
						backgroundColor: getRandomColor(),
					} as BlockStyleMap,
				};
				const childBlock = parentBlock.addChild(child);
				childBlock.selectBlock();
				const parentElement = document.body.querySelector(
					`.canvas [data-block-id="${parentBlock.blockId}"]`
				) as HTMLElement;
				parentBlock.setStyle("position", "relative");
				const parentElementBounds = parentElement.getBoundingClientRect();
				let x = (ev.x - parentElementBounds.left) / store.canvas.scale;
				let y = (ev.y - parentElementBounds.top) / store.canvas.scale;
				childBlock.setStyle("position", "absolute");
				childBlock.setStyle("top", addPxToNumber(y));
				childBlock.setStyle("left", addPxToNumber(x));

				const initialX = ev.clientX;
				const initialY = ev.clientY;

				const mouseMoveHandler = (ev: MouseEvent) => {
					ev.preventDefault();
					let width = (ev.clientX - initialX) / store.canvas.scale;
					let height = (ev.clientY - initialY) / store.canvas.scale;

					width = clamp(width, 10, width);
					height = clamp(height, 10, height);
					childBlock.setStyle("width", addPxToNumber(width));
					childBlock.setStyle("height", addPxToNumber(height));
				};

				document.addEventListener("mousemove", mouseMoveHandler);

				document.addEventListener(
					"mouseup",
					() => {
						childBlock.setStyle("position", "static");
						childBlock.setStyle("top", "auto");
						childBlock.setStyle("left", "auto");
						container.style.cursor = "auto";
						container.removeEventListener("mousedown", addContainer);
						document.removeEventListener("mousemove", mouseMoveHandler);
						setTimeout(() => {
							store.builderState.mode = "select";
						}, 50);
					},
					{ once: true }
				);
			}
		};
		container.addEventListener("mousedown", addContainer);
	}

	if (mode === "image") {
		const container = document.body.querySelector(".canvas-container") as HTMLElement;
		container.style.cursor = "crosshair";
		const canvas = document.body.querySelector(".canvas") as HTMLElement;

		const addImage = (ev: MouseEvent) => {
			ev.preventDefault();
			let element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
			// check if element contains data-block-id
			if (element) {
				let block = store.builderState.blocks[0];
				if (element.dataset.blockId) {
					block = store.findBlock(element.dataset.blockId) || block;
				}
				const child: BlockOptions = {
					name: "Image",
					element: "img",
					icon: "image",
					attributes: {
						src: "https://user-images.githubusercontent.com/13928957/212847544-5773795d-2fd6-48d1-8423-b78ecc92522b.png",
					},
					styles: {
						width: "0px",
						height: "0px",
						objectFit: "cover",
					} as BlockStyleMap,
				};
				const childBlock = block.addChild(child);
				if (block.blockId === "root") {
					const rootElement = document.body.querySelector(".canvas > [data-block-id='root']") as HTMLElement;
					rootElement.style.position = "relative";
					const rootBounds = rootElement.getBoundingClientRect();
					let x = (ev.x - rootBounds.left) / store.canvas.scale;
					let y = (ev.y - rootBounds.top) / store.canvas.scale;
					childBlock.setStyle("position", "absolute");
					childBlock.setStyle("top", addPxToNumber(y));
					childBlock.setStyle("left", addPxToNumber(x));
				}

				const initialX = ev.clientX;
				const initialY = ev.clientY;

				const mouseMoveHandler = (ev: MouseEvent) => {
					ev.preventDefault();
					const width = (ev.clientX - initialX) / store.canvas.scale;
					const height = (ev.clientY - initialY) / store.canvas.scale;

					childBlock.setStyle("width", addPxToNumber(width));
					childBlock.setStyle("height", addPxToNumber(height));
				};

				document.addEventListener("mousemove", mouseMoveHandler);

				document.addEventListener(
					"mouseup",
					(ev) => {
						ev.preventDefault();
						childBlock.setStyle("position", "static");
						childBlock.setStyle("top", "auto");
						childBlock.setStyle("left", "auto");
						childBlock.selectBlock();
						container.style.cursor = "auto";
						document.removeEventListener("mousemove", mouseMoveHandler);
						canvas.removeEventListener("mousedown", addImage);
						setTimeout(() => {
							store.builderState.mode = "select";
						}, 50);
					},
					{ once: true }
				);
			}
		};
		canvas.addEventListener("mousedown", addImage);
	}
};
</script>
