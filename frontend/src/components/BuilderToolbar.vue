<template>
	<div class="toolbar flex h-14 items-center justify-center bg-white p-2 shadow-sm" ref="toolbar">
		<div class="absolute left-3 flex items-center">
			<router-link class="flex items-center" :to="{ name: 'home' }">
				<img src="/frappe_black.png" alt="logo" class="h-5 dark:hidden" />
				<img src="/frappe_white.png" alt="logo" class="hidden h-5 dark:block" />
				<h1 class="text-base text-gray-800 dark:text-gray-200">Builder</h1>
			</router-link>
		</div>
		<div class="ml-10 flex gap-3">
			<Button
				variant="ghost"
				v-for="mode in [
					{ mode: 'select', icon: 'mouse-pointer' },
					{ mode: 'text', icon: 'type' },
					{ mode: 'container', icon: 'square' },
					{ mode: 'image', icon: 'image' },
				] as { 'mode': BuilderMode; 'icon': string }[]"
				:icon="mode.icon"
				class="!text-gray-700 dark:bg-transparent dark:!text-gray-200 hover:dark:bg-zinc-800 focus:dark:bg-zinc-700 active:dark:bg-zinc-700"
				@click="store.builderState.mode = mode.mode"
				:active="store.builderState.mode === mode.mode"></Button>
		</div>
		<div class="absolute right-3 flex items-center">
			<Popover transition="default" placement="bottom-start" class="inline w-full">
				<template #target="{ togglePopover, isOpen }">
					<div>
						<FeatherIcon
							name="settings"
							class="mr-4 h-4 w-4 cursor-pointer text-gray-600 dark:text-gray-400"
							@click="togglePopover"></FeatherIcon>
					</div>
				</template>
				<template #body-main class="p-3">
					<div class="flex flex-row flex-wrap gap-5 p-3">
						<Input
							type="text"
							class="w-full text-sm"
							label="Page Title"
							:value="pageData.page_title"
							@change="pageResource.setValue.submit({ page_title: $event })" />
						<Input
							type="text"
							class="w-full text-sm"
							label="URL"
							v-model="pageData.route"
							:value="pageData.route"
							@change="pageResource.setValue.submit({ route: $event })" />
					</div>
				</template>
			</Popover>
			<UseDark v-slot="{ isDark, toggleDark }">
				<FeatherIcon
					:name="isDark ? 'moon' : 'sun'"
					class="mr-4 h-4 w-4 cursor-pointer text-gray-600 dark:text-gray-400"
					@click="toggleDark()" />
			</UseDark>
			<Button variant="solid" @click="publish" class="border-0 text-xs">Preview</Button>
		</div>
	</div>
</template>
<script setup lang="ts">
import { WebPageBeta } from "@/types/WebsiteBuilder/WebPageBeta";
import { addPxToNumber, getNumberFromPx, getRandomColor } from "@/utils/helpers";
import { UseDark } from "@vueuse/components";
import { clamp, useEventListener } from "@vueuse/core";
import { Popover, createDocumentResource, createResource } from "frappe-ui";
import { Ref, onMounted, ref, watch, watchEffect } from "vue";
import useStore from "../store";

const store = useStore();
const toolbar = ref(null);

const pageData = ref({}) as unknown as Ref<WebPageBeta>;

const publishWebResource = createResource({
	url: "website_builder.api.publish",
	onSuccess(page: any) {
		// hack
		page.blocks = JSON.parse(page.blocks);
		store.pages[page.name] = page as WebPageBeta;
		store.pageName = page.page_name;
		window.open(`/${page.route}`, "_blank");
	},
});

let pageResource = {};

watchEffect(() => {
	if (store.builderState.selectedPage && pageData.value.name !== store.builderState.selectedPage) {
		pageResource = createDocumentResource({
			doctype: "Web Page Beta",
			name: store.builderState.selectedPage,
			auto: true,
		});
		pageData.value = pageResource.doc;
	}
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

onMounted(() => {
	setEvents();
});

function setEvents() {
	const container = document.body.querySelector(".canvas-container") as HTMLElement;
	useEventListener(container, "mousedown", (ev: MouseEvent) => {
		const initialX = ev.clientX;
		const initialY = ev.clientY;
		if (store.builderState.mode === "select") {
			return;
		} else {
			ev.stopPropagation();
			let element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
			let block = store.builderState.blocks[0];
			if (element) {
				if (element.dataset.blockId) {
					block = store.findBlock(element.dataset.blockId) || block;
				}
			}
			let parentBlock = store.builderState.blocks[0];
			if (element.dataset.blockId) {
				parentBlock = store.findBlock(element.dataset.blockId) || parentBlock;
				while (parentBlock && !parentBlock.canHaveChildren()) {
					parentBlock = parentBlock.getParentBlock() || store.builderState.blocks[0];
				}
			}
			let child;
			if (store.builderState.mode === "text") {
				child = {
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
			} else if (store.builderState.mode === "image") {
				child = {
					name: "Image",
					element: "img",
					icon: "image",
					styles: {
						objectFit: "cover",
					} as BlockStyleMap,
				};
			} else {
				child = {
					name: "Container",
					element: "div",
					icon: "square",
					styles: {
						background: "#94E6FF",
					} as BlockStyleMap,
				};
			}
			const childBlock = parentBlock.addChild(child);
			childBlock.selectBlock();

			const parentElement = document.body.querySelector(
				`.canvas [data-block-id="${parentBlock.blockId}"]`
			) as HTMLElement;
			const parentOldPosition = parentBlock.getStyle("position");
			parentBlock.setBaseStyle("position", parentOldPosition || "relative");
			const parentElementBounds = parentElement.getBoundingClientRect();
			let x = (ev.x - parentElementBounds.left) / store.canvas.scale;
			let y = (ev.y - parentElementBounds.top) / store.canvas.scale;
			const parentWidth = getNumberFromPx(getComputedStyle(parentElement).width);
			const parentHeight = getNumberFromPx(getComputedStyle(parentElement).height);
			childBlock.setBaseStyle("position", "absolute");
			childBlock.setBaseStyle("top", addPxToNumber(y));
			childBlock.setBaseStyle("left", addPxToNumber(x));

			const mouseMoveHandler = (mouseMoveEvent: MouseEvent) => {
				if (store.builderState.mode === "text") {
					return;
				} else {
					mouseMoveEvent.preventDefault();
					let width = (mouseMoveEvent.clientX - initialX) / store.canvas.scale;
					let height = (mouseMoveEvent.clientY - initialY) / store.canvas.scale;
					width = clamp(width, 0, parentWidth);
					height = clamp(height, 0, parentHeight);
					childBlock.setBaseStyle("width", addPxToNumber(width));
					childBlock.setBaseStyle("height", addPxToNumber(height));
				}
			};
			useEventListener(document, "mousemove", mouseMoveHandler);
			useEventListener(
				document,
				"mouseup",
				() => {
					document.removeEventListener("mousemove", mouseMoveHandler);
					setTimeout(() => {
						store.builderState.mode = "select";
					}, 50);
					if (store.builderState.mode === "text") {
						return;
					}
					childBlock.setBaseStyle("position", "static");
					if (getNumberFromPx(childBlock.getStyle("width")) < 100) {
						childBlock.setBaseStyle("width", "100%");
					}
					if (getNumberFromPx(childBlock.getStyle("height")) < 100) {
						childBlock.setBaseStyle("height", "200px");
					}
					childBlock.setBaseStyle("top", "auto");
					childBlock.setBaseStyle("left", "auto");
					parentBlock.setBaseStyle("position", parentOldPosition || "static");
				},
				{ once: true }
			);
		}
	});
}

function toggleMode(mode: BuilderMode) {
	const container = document.body.querySelector(".canvas-container") as HTMLElement;
	if (mode === "text") {
		container.style.cursor = "text";
	} else if (mode === "select") {
		container.style.cursor = "default";
	} else {
		container.style.cursor = "crosshair";
	}
}
</script>
