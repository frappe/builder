<template>
	<div class="flex h-[90vh] max-h-[800px] overflow-hidden">
		<div class="flex w-48 shrink-0 flex-col gap-5 bg-surface-gray-1 p-4 px-2">
			<span class="px-2 text-lg font-semibold text-ink-gray-9">Settings</span>
			<div class="flex flex-col" v-for="(item, index) in settingsSidebarItems" :key="index">
				<span class="mb-2 px-2 text-base font-medium text-ink-gray-5">
					{{ item.title }}
				</span>
				<a
					@click="!link.disabled && selectItem(link.value)"
					class="flex cursor-pointer items-center gap-2 rounded p-2 py-[5px] text-base text-ink-gray-8"
					:class="{
						'bg-surface-selected shadow-sm': selectedItem === link.value,
						'!text-ink-gray-3': link.disabled,
					}"
					v-for="link in item.items">
					<component v-if="link?.icon" :is="link?.icon" class="h-4 w-4" />
					{{ link.label }}
				</a>
			</div>
		</div>
		<div class="flex flex-1 flex-col gap-5 overflow-hidden bg-surface-white p-14 px-16">
			<h2 class="text-xl font-semibold leading-none">{{ selectedItemDoc?.title }}</h2>
			<BuilderButton
				icon="x"
				variant="subtle"
				@click="$emit('close')"
				class="absolute right-5 top-5"></BuilderButton>
			<component :is="selectedItemDoc?.component" />
		</div>
	</div>
</template>
<script setup lang="ts">
import RedirectIcon from "@/components/Icons/Redirect.vue";
import GlobalRedirects from "@/components/Settings/GlobalRedirects.vue";
import PageCode from "@/components/Settings/PageCode.vue";
import usePageStore from "@/stores/pageStore";
import { computed, onActivated, ref } from "vue";
import { useRoute } from "vue-router";
import ChartIcon from "./Icons/Chart.vue";
import CodeIcon from "./Icons/Code.vue";
import MetaIcon from "./Icons/Meta.vue";
import SettingsIcon from "./Icons/Settings.vue";
import GlobalAnalytics from "./Settings/GlobalAnalytics.vue";
import GlobalCode from "./Settings/GlobalCode.vue";
import GlobalGeneral from "./Settings/GlobalGeneral.vue";
import PageAnalytics from "./Settings/PageAnalytics.vue";
import PageGeneral from "./Settings/PageGeneral.vue";
import PageMeta from "./Settings/PageMeta.vue";

const props = defineProps<{
	onlyGlobal?: boolean;
}>();

const route = useRoute();
const pageStore = usePageStore();
const emit = defineEmits(["close"]);
const selectedItem = ref<string>(props.onlyGlobal ? "global_general" : "page_general");

type SidebarItem = {
	label: string;
	value: string;
	component: any;
	title: string;
	// prettier-ignore
	icon?: typeof import("*.vue");
	disabled?: boolean;
};

const selectedItemDoc = computed(() => {
	for (const item of settingsSidebarItems) {
		for (const link of item.items) {
			if (link.value === selectedItem.value) {
				return link;
			}
		}
	}
});

const pageSettings = {
	title: "Current Page",
	items: [
		{
			label: "General",
			value: "page_general",
			component: PageGeneral,
			title: "General",
			icon: SettingsIcon,
		},
		{ label: "Code", value: "page_code", component: PageCode, title: "Page Code", icon: CodeIcon },
		{ label: "Meta", value: "page_meta", component: PageMeta, title: "Meta", icon: MetaIcon },
		{
			label: "Analytics",
			value: "page_analytics",
			component: PageAnalytics,
			title: "Analytics",
			icon: ChartIcon,
		},
	],
};

const globalSettings = {
	title: "Global",
	items: [
		{
			label: "General",
			value: "global_general",
			component: GlobalGeneral,
			title: "General",
			icon: SettingsIcon,
			disabled: false,
		},
		{ label: "Code", value: "global_code", component: GlobalCode, title: "Global Code", icon: CodeIcon },
		{
			label: "Redirects",
			value: "global_redirects",
			component: GlobalRedirects,
			title: "Redirects",
			icon: RedirectIcon,
		},
		{
			label: "Analytics",
			value: "global_analytics",
			component: GlobalAnalytics,
			title: "Analytics",
			icon: ChartIcon,
		},
	],
};

const settingsSidebarItems = [globalSettings];
if (!props.onlyGlobal) settingsSidebarItems.unshift(pageSettings);

const selectItem = (value: string) => {
	selectedItem.value = value;
};

onActivated(() => {
	if (route.params.pageId === pageStore.activePage?.name) return;
	else if (route.params.pageId) {
		pageStore.setActivePage(route.params.pageId as string);
	}
});
</script>
