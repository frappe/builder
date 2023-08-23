<template>
	<div class="flex flex-col items-center justify-center bg-gray-100 p-5 dark:bg-zinc-900">
		<div class="w-full">
			<router-link
				:to="{ name: 'builder', params: { pageId: route.params.pageId } }"
				class="flex w-fit text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 hover:dark:text-gray-100">
				<FeatherIcon name="arrow-left" class="mr-4 h-4 w-4 cursor-pointer" />
				Back to builder
			</router-link>
		</div>
		<div
			class="relative mt-5 flex h-[90vh] bg-white"
			:style="{
				width: width + 'px',
			}">
			<PanelResizer
				class="ml-[-12px]"
				side="left"
				:width="width"
				:minWidth="minWidth"
				:maxWidth="maxWidth"
				@resize="(val) => (width = val)">
				<div class="resize-handler-left h-full w-2 rounded-sm bg-gray-200 dark:bg-zinc-600"></div>
			</PanelResizer>
			<iframe
				:src="previewRoute"
				frameborder="0"
				v-if="previewRoute"
				class="flex-1 rounded-sm"
				ref="previewWindow"></iframe>
			<div
				v-if="loading"
				class="absolute flex h-full w-full flex-1 items-center justify-center bg-white bg-opacity-50 text-gray-600">
				Loading...
			</div>
			<PanelResizer
				class="mr-[-8px]"
				side="right"
				:width="width"
				:minWidth="minWidth"
				:maxWidth="maxWidth"
				@resize="(val) => (width = val)">
				<div class="resize-handler-left h-full w-2 rounded-sm bg-gray-200 dark:bg-zinc-600"></div>
			</PanelResizer>
		</div>
	</div>
</template>
<script lang="ts" setup>
import PanelResizer from "@/components/PanelResizer.vue";
import { useEventListener } from "@vueuse/core";
import { Ref, onMounted, ref, watchEffect } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
const maxWidth = window.innerWidth * 0.92;
const minWidth = 480;
let previewRoute = ref("");
const width = ref(maxWidth);
const loading = ref(false);

const previewWindow = ref(null) as Ref<HTMLIFrameElement | null>;

useEventListener(document, "keydown", (ev) => {
	if (ev.key === "Escape") {
		history.back();
	}
});

// hack to relay mouseup event from iframe to parent
watchEffect(() => {
	if (previewWindow.value) {
		loading.value = true;
		previewWindow.value.addEventListener("load", () => {
			setTimeout(() => {
				loading.value = false;
			}, 100);
			previewWindow.value?.addEventListener("mousedown", (ev) => {
				document.dispatchEvent(new MouseEvent("mousedown", ev));
			});
			previewWindow.value?.contentWindow?.document.addEventListener("mouseup", (ev) => {
				document.dispatchEvent(new MouseEvent("mouseup", ev));
			});
		});
	}
});

onMounted(() => {
	previewRoute.value = `/api/method/website_builder.website_builder.doctype.web_page_beta.web_page_beta.get_page_preview_html?page=${route.params.pageId}`;
});
</script>
