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
					{ mode: 'html', icon: 'code'}
				] as { 'mode': BuilderMode; 'icon': string }[]"
				:icon="mode.icon"
				class="!text-gray-700 dark:bg-transparent dark:!text-gray-200 hover:dark:bg-zinc-800 focus:dark:bg-zinc-700 active:dark:bg-zinc-700"
				@click="store.mode = mode.mode"
				:active="store.mode === mode.mode"></Button>
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
							@change="webPages.setValue.submit({ name: pageData.name, page_title: $event })" />
						<Input
							type="text"
							class="w-full text-sm"
							label="URL"
							v-model="pageData.route"
							:value="pageData.route"
							@change="webPages.setValue.submit({ name: pageData.name, route: $event })" />
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
import { UseDark } from "@vueuse/components";
import { Popover, createResource } from "frappe-ui";
import { PropType, Ref, ref, watch } from "vue";

import { webPages } from "@/data/webPage";

import useStore from "../store";

const store = useStore();
const toolbar = ref(null);

const pageData = ref({}) as unknown as Ref<WebPageBeta>;
defineProps({
	canvasProps: {
		type: Object as PropType<CanvasProps>,
		required: true,
	},
});

const publishWebResource = createResource({
	url: "website_builder.api.publish",
	onSuccess(page: WebPageBeta) {
		page.blocks = JSON.parse(page.blocks);
		store.pageName = page.page_name || page.name;
		window.open(`/${page.route}`, "preview-page");
	},
});

watch(
	() => store.selectedPage,
	() => {
		if (store.selectedPage && pageData.value.name !== store.selectedPage) {
			webPages.fetchOne.submit(store.selectedPage).then((data: WebPageBeta[]) => {
				pageData.value = data[0];
			});
		}
	}
);

const publish = () => {
	publishWebResource.submit({
		blocks: store.getPageData(),
		page_name: store.pageName,
	});
};

watch(
	() => store.mode,
	() => {
		toggleMode(store.mode);
	}
);

function toggleMode(mode: BuilderMode) {
	const container = document.body.querySelector(".canvas-container") as HTMLElement;
	if (mode === "text") {
		container.style.cursor = "text";
	} else if (["container", "image", "html"].includes(mode)) {
		container.style.cursor = "crosshair";
	} else {
		container.style.cursor = "default";
	}
}
</script>
