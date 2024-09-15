<template>
	<div class="flex h-[90vh] max-h-[800px] overflow-hidden">
		<div class="flex w-48 flex-col gap-5 bg-surface-menu-bar p-4 px-2">
			<span class="px-2 text-lg font-semibold text-text-icons-gray-9">Settings</span>
			<div class="flex flex-col" v-for="(item, index) in settingsSidebarItems" :key="index">
				<span class="mb-2 px-2 text-base font-medium text-text-icons-gray-5">
					{{ item.title }}
				</span>
				<a
					@click="() => selectItem(link.value)"
					class="flex cursor-pointer items-center gap-2 rounded p-2 py-[5px] text-base text-text-icons-gray-8"
					:class="{
						'bg-surface-selected shadow-sm': selectedItem === link.value,
					}"
					v-for="link in item.items">
					<component v-if="link?.icon" :is="link?.icon" class="h-4 w-4 text-text-icons-gray-5" />
					{{ link.label }}
				</a>
			</div>
		</div>
		<div class="flex flex-1 flex-col gap-5 bg-surface-white p-14 px-16 dark:bg-zinc-900">
			<h2 class="text-xl font-semibold leading-none">{{ selectedItemDoc?.title }}</h2>
			<Button icon="x" variant="subtle" @click="$emit('close')" class="absolute right-5 top-5"></Button>
			<component :is="selectedItemDoc?.component" />
		</div>
	</div>
</template>
<script setup lang="ts">
import Button from "@/components/Controls/Button.vue";
import RedirectIcon from "@/components/Icons/Redirect.vue";
import GlobalRedirects from "@/components/Settings/GlobalRedirects.vue";
import useStore from "@/store";
import { computed, onActivated, ref } from "vue";
import { useRoute } from "vue-router";
import ChartIcon from "./Icons/Chart.vue";
import CodeIcon from "./Icons/Code.vue";
import MetaIcon from "./Icons/Meta.vue";
import SettingsIcon from "./Icons/Settings.vue";
import GlobalCode from "./Settings/GlobalCode.vue";
import GlobalGeneral from "./Settings/GlobalGeneral.vue";
import PageAnalytics from "./Settings/PageAnalytics.vue";
import PageGeneral from "./Settings/PageGeneral.vue";
import PageMeta from "./Settings/PageMeta.vue";

const props = defineProps<{
	onlyGlobal?: boolean;
}>();

const route = useRoute();
const store = useStore();
const emit = defineEmits(["close"]);
const selectedItem = ref<string>(props.onlyGlobal ? "global_general" : "page_general");

type SidebarItem = {
	label: string;
	value: string;
	component: any;
	title: string;
	// prettier-ignore
	icon?: typeof import("*.vue");
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
		},
		{ label: "Code", value: "global_code", component: GlobalCode, title: "Code", icon: CodeIcon },
		{
			label: "Redirects",
			value: "global_redirects",
			component: GlobalRedirects,
			title: "Redirects",
			icon: RedirectIcon,
		},
	],
};

const settingsSidebarItems = [globalSettings];
if (!props.onlyGlobal) settingsSidebarItems.unshift(pageSettings);

const selectItem = (value: string) => {
	selectedItem.value = value;
};

onActivated(() => {
	if (route.params.pageId === store.activePage?.name) return;
	else if (route.params.pageId) {
		store.setActivePage(route.params.pageId as string);
	}
});
</script>
