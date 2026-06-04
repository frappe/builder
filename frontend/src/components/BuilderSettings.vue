<template>
	<div class="flex h-[88vh] max-h-[800px] overflow-hidden">
		<div class="flex w-48 shrink-0 flex-col gap-5 bg-surface-gray-1 p-4 px-2">
			<span class="px-2 text-lg font-semibold text-ink-gray-9">Settings</span>
			<div class="flex flex-col" v-for="(item, index) in settingsSidebarItems" :key="index">
				<span class="mb-2 px-2 text-base font-medium text-ink-gray-5">
					{{ item.title }}
				</span>
				<Button
					v-for="link in item.items"
					:variant="selectedItem === link.value ? 'subtle' : 'ghost'"
					:disabled="link.disabled"
					:icon-left="link.icon"
					@click="!link.disabled && selectItem(link.value)"
					:class="{
						'!bg-surface-gray-3': selectedItem === link.value,
					}"
					class="!justify-start">
					{{ link.label }}
				</Button>
			</div>
		</div>
		<div class="flex flex-1 flex-col gap-5 overflow-hidden bg-surface-white p-14 px-16 pb-0">
			<h2 class="text-xl font-semibold leading-none text-ink-gray-9">{{ selectedItemDoc?.title }}</h2>
			<Button
				icon="lucide-x"
				variant="subtle"
				@click="$emit('close')"
				class="absolute right-5 top-5"></Button>
			<component :is="selectedItemDoc?.component" v-if="settingsLoaded" class="pb-16" />
			<div v-else class="flex items-center justify-center">
				<span class="text-ink-gray-5">Loading...</span>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import GlobalRedirects from "@/components/Settings/GlobalRedirects.vue";
import PageCode from "@/components/Settings/PageCode.vue";
import builderProjectFolder from "@/data/builderProjectFolder";
import { builderSettings } from "@/data/builderSettings";
import usePageStore from "@/stores/pageStore";
import { computed, onActivated, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import GlobalAI from "./Settings/GlobalAI.vue";
import GlobalAnalytics from "./Settings/GlobalAnalytics.vue";
import GlobalCode from "./Settings/GlobalCode.vue";
import GlobalDeveloper from "./Settings/GlobalDeveloper.vue";
import GlobalDomains from "./Settings/GlobalDomains.vue";
import GlobalGeneral from "./Settings/GlobalGeneral.vue";
import PageAnalytics from "./Settings/PageAnalytics.vue";
import PageGeneral from "./Settings/PageGeneral.vue";
import PageMeta from "./Settings/PageMeta.vue";

const props = defineProps<{
	onlyGlobal?: boolean;
	initialTab?: string;
}>();

const route = useRoute();
const pageStore = usePageStore();
const emit = defineEmits(["close"]);
const selectedItem = ref<string>(props.initialTab || (props.onlyGlobal ? "global_general" : "page_general"));
const settingsLoaded = ref(false);

onMounted(async () => {
	const promises = [];
	if (!builderSettings.doc) {
		promises.push(builderSettings.reload());
	}
	if (!builderProjectFolder.data) {
		promises.push(builderProjectFolder.fetch());
	}
	await Promise.all(promises);
	settingsLoaded.value = true;
});

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
			icon: "lucide-settings",
		},
		{ label: "Code", value: "page_code", component: PageCode, title: "Page Code", icon: "lucide-code" },
		{
			label: "Meta",
			value: "page_meta",
			component: PageMeta,
			title: "Meta",
			icon: "lucide-square-dashed-bottom-code",
		},
		{
			label: "Analytics",
			value: "page_analytics",
			component: PageAnalytics,
			title: "Page Views",
			icon: "lucide-chart-bar",
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
			icon: "lucide-settings",
			disabled: false,
		},
		{ label: "Code", value: "global_code", component: GlobalCode, title: "Global Code", icon: "lucide-code" },
		{
			label: "Redirects",
			value: "global_redirects",
			component: GlobalRedirects,
			title: "Redirects",
			icon: "lucide-shuffle",
		},
		...(window.is_fc_site || window.is_developer_mode
			? [
					{
						label: "Domains",
						value: "global_domains",
						component: GlobalDomains,
						title: "Custom Domains",
						icon: "lucide-globe",
					},
				]
			: []),
		{
			label: "Analytics",
			value: "global_analytics",
			component: GlobalAnalytics,
			title: "Site Views",
			icon: "lucide-chart-bar",
		},
		{
			label: "Developer",
			value: "global_developer",
			component: GlobalDeveloper,
			title: "Developer Settings",
			icon: "lucide-terminal",
		},
		{
			label: "AI",
			value: "global_ai",
			component: GlobalAI,
			title: "AI Settings",
			icon: "lucide-sparkles",
		},
	],
};

const settingsSidebarItems = [globalSettings];
if (!props.onlyGlobal) settingsSidebarItems.unshift(pageSettings);

const selectItem = (value: string) => {
	selectedItem.value = value;
};

watch(
	() => props.initialTab,
	(tab) => {
		if (tab) selectItem(tab);
	},
);

defineExpose({ selectItem });

onActivated(() => {
	if (route.params.pageId === pageStore.activePage?.name) return;
	else if (route.params.pageId) {
		pageStore.setActivePage(route.params.pageId as string);
	}
});
</script>
