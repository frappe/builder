<template>
	<Popover side="bottom" align="center" :offset="20" bare v-model:open="showPopover">
		<template #trigger>
			<div class="flex cursor-pointer items-center gap-2 p-2 text-ink-gray-8">
				<div class="flex h-6 items-center text-base text-ink-gray-6" v-if="!pageStore.activePage">
					{{ __("Loading...") }}
				</div>
				<div v-else class="flex items-center gap-1">
					<Tooltip :text="__('This is the homepage for your site')" :hoverDelay="0.6">
						<span
							class="lucide-home h-[14px] w-4"
							aria-hidden="true"
							v-if="pageStore.isHomePage(pageStore.activePage)" />
					</Tooltip>
					<Tooltip :text="__('This page has limited access')" :hoverDelay="0.6">
						<span
							class="lucide-shield-user size-4 text-ink-amber-6"
							v-if="pageStore.activePage?.published && pageStore.activePage?.authenticated_access" />
					</Tooltip>
					<Tooltip :text="__('Publicly accessible')" :hoverDelay="0.6">
						<span
							class="lucide-globe mr-1 h-[14px] w-[14px] !text-gray-700 dark:!text-gray-200"
							v-if="pageStore.activePage?.published && !pageStore.activePage?.authenticated_access" />
					</Tooltip>
					<span
						class="max-w-48 truncate text-base text-ink-gray-8"
						:title="pageStore?.activePage?.page_title || __('My Page')">
						{{ pageStore?.activePage?.page_title || __("My Page") }}
					</span>
					-
					<span
						class="max-w-96 truncate text-base text-ink-gray-5"
						v-html="routeString"
						:title="getTextContent(routeString)"></span>
				</div>
				<span
					class="lucide-external-link h-[14px] w-[14px] !text-gray-700 dark:!text-gray-200"
					aria-hidden="true"
					v-if="pageStore.activePage && pageStore.activePage.published"
					@click.stop="pageStore.openPageInBrowser(pageStore.activePage as BuilderPage)" />
			</div>
		</template>
		<template #default>
			<div class="flex w-72 flex-col gap-3 rounded bg-surface-base p-4 shadow-lg" v-if="pageStore.activePage">
				<PageOptions></PageOptions>
			</div>
		</template>
	</Popover>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import PageOptions from "@/components/PageOptions.vue";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/doctypes";
import { getTextContent } from "@/utils/helpers";
import { Popover, Tooltip } from "frappe-ui";
import { computed, ref, watch } from "vue";

const pageStore = usePageStore();
const builderStore = useBuilderStore();
const showPopover = ref(false);

watch(
	() => builderStore.isSmallScreen,
	(isSmallScreen) => {
		if (isSmallScreen) {
			showPopover.value = false;
		}
	},
);

const routeString = computed(() => {
	const route = pageStore.activePage?.route || "/";
	const routeStringToReturn = route.split("/").map((part) => {
		let variable = "";
		let formattedPart = part;

		if (part.startsWith(":")) {
			variable = part.slice(1);
		} else if (part.startsWith("<")) {
			variable = part.slice(1, -1);
			formattedPart = `&lt;${variable}&gt;`;
		}
		if (variable) {
			const previewValue = pageStore.routeVariables[variable];
			return `<span class="${
				previewValue ? "bg-purple-100 dark:bg-purple-900" : "bg-gray-100 dark:bg-gray-800"
			} rounded-sm px-[5px] pb-[2px] text-sm">${previewValue || formattedPart}</span>`;
		} else {
			return formattedPart;
		}
	});
	return routeStringToReturn.join("/");
});
</script>
