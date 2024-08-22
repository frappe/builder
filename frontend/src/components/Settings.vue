<template>
	<div class="flex h-[80vh] overflow-hidden">
		<div class="flex w-48 flex-col gap-5 bg-gray-50 p-4 px-3">
			<span class="px-2 py-1 text-xl font-semibold text-gray-900 dark:text-zinc-200">Settings</span>
			<div class="flex flex-col" v-for="(item, index) in settingsSidebarItems" :key="index">
				<span class="mb-2 px-3 text-base font-semibold text-gray-900 dark:text-zinc-200">
					{{ item.title }}
				</span>
				<a
					@click="() => selectItem(link.value)"
					class="cursor-pointer rounded p-2 px-3 text-base text-gray-800 dark:text-zinc-500"
					:class="{
						'bg-white text-gray-800 shadow-sm dark:bg-zinc-900 dark:!text-zinc-300':
							selectedItem === link.value,
					}"
					v-for="link in item.items">
					{{ link.label }}
				</a>
			</div>
		</div>
		<div class="flex h-full flex-1 flex-col gap-5 bg-white p-5 dark:bg-zinc-900">
			<div class="flex justify-between">
				<span class="text-xl font-semibold text-gray-800 dark:text-zinc-200">
					{{ selectedItemDoc?.title }}
				</span>
				<Button icon="x" @click="$emit('close')"></Button>
			</div>
			<component :is="(selectedItemDoc as SidebarItem).component" />
		</div>
	</div>
</template>
<script setup lang="ts">
import useStore from "@/store";
import { computed, onActivated, ref } from "vue";
import PageGeneral from "./Settings/PageGeneral.vue";
// check route for page id
import { useRoute } from "vue-router";
import GlobalAnalytics from "./Settings/GlobalAnalytics.vue";
import GlobalGeneral from "./Settings/GlobalGeneral.vue";
import GlobalMeta from "./Settings/GlobalMeta.vue";
import PageAnalytics from "./Settings/PageAnalytics.vue";
import PageMeta from "./Settings/PageMeta.vue";
import PageRobots from "./Settings/PageRobots.vue";
const route = useRoute();
const store = useStore();
const emit = defineEmits(["close"]);

const selectedItem = ref<string>("page_general");

type SidebarItem = {
	label: string;
	value: string;
	component: any;
	title: string;
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

const settingsSidebarItems = [
	{
		title: "Page",
		items: [
			{ label: "General", value: "page_general", component: PageGeneral, title: "General" },
			{ label: "Meta", value: "page_meta", component: PageMeta, title: "Meta" },
			{ label: "Robots", value: "page_robots", component: PageRobots, title: "Robots" },
			{ label: "Analytics", value: "page_analytics", component: PageAnalytics, title: "Analytics" },
		],
	},
	{
		title: "Global",
		items: [
			{ label: "General", value: "global_general", component: GlobalGeneral, title: "General" },
			{ label: "Meta", value: "global_meta", component: GlobalMeta, title: "Meta" },
			{ label: "Analytics", value: "global_analytics", component: GlobalAnalytics, title: "Analytics" },
		],
	},
];

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
