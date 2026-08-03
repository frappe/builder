<template>
	<div class="flex h-[88vh] max-h-[800px] overflow-hidden">
		<div class="flex w-48 shrink-0 flex-col gap-5 bg-surface-gray-1 p-4 px-2">
			<span class="text-lg-semibold px-2 text-ink-gray-9">设置</span>
			<div class="flex flex-col gap-0.5" v-for="(item, index) in settingsSidebarItems" :key="index">
				<span class="text-base-medium mb-2 px-2 text-ink-gray-5">
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
		<div class="flex flex-1 flex-col gap-5 overflow-hidden bg-surface-base p-14 px-16 pb-0">
			<h2 class="text-2xl-semibold leading-none text-ink-gray-9">{{ selectedItemDoc?.title }}</h2>
			<Button
				icon="lucide-x"
				variant="subtle"
				@click="$emit('close')"
				class="absolute right-5 top-5"></Button>
			<KeepAlive v-if="settingsLoaded">
				<component :is="selectedItemDoc?.component" class="pb-16" />
			</KeepAlive>
			<div v-else class="flex items-center justify-center">
				<span class="text-ink-gray-5">加载中...</span>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import GlobalRedirects from "@/components/Settings/GlobalRedirects.vue";
import PageCode from "@/components/Settings/PageCode.vue";
import PageRobots from "@/components/Settings/PageRobots.vue";
import builderProjectFolder from "@/data/builderProjectFolder";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { computed, onActivated, onMounted, provide, ref, watch } from "vue";
import { useRoute } from "vue-router";
import GlobalAI from "./Settings/GlobalAI.vue";
import GlobalAnalytics from "./Settings/GlobalAnalytics.vue";
import GlobalCode from "./Settings/GlobalCode.vue";
import GlobalDeveloper from "./Settings/GlobalDeveloper.vue";
import GlobalDomains from "./Settings/GlobalDomains.vue";
import GlobalGeneral from "./Settings/GlobalGeneral.vue";
import GlobalUsers from "./Settings/GlobalUsers.vue";
import PageAnalytics from "./Settings/PageAnalytics.vue";
import PageGeneral from "./Settings/PageGeneral.vue";
import PageMeta from "./Settings/PageMeta.vue";

const props = defineProps<{
	onlyGlobal?: boolean;
	initialTab?: string;
}>();

const route = useRoute();
const pageStore = usePageStore();
const builderStore = useBuilderStore();
const emit = defineEmits(["close"]);
const selectedItem = ref<string>(
	props.initialTab ||
		builderStore.settingsActiveTab ||
		(props.onlyGlobal ? "global_general" : "page_general"),
);
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
	title: "当前页面",
	items: [
		{
			label: "常规",
			value: "page_general",
			component: PageGeneral,
			title: "常规",
			icon: "lucide-settings",
		},
		{ label: "代码", value: "page_code", component: PageCode, title: "页面代码", icon: "lucide-code" },
		{
			label: "元数据",
			value: "page_meta",
			component: PageMeta,
			title: "元数据",
			icon: "lucide-square-dashed-bottom-code",
		},
		{
			label: "分析",
			value: "page_analytics",
			component: PageAnalytics,
			title: "页面分析",
			icon: "lucide-chart-bar",
		},
	],
};

const globalSettings = {
	title: "全局",
	items: [
		{
			label: "常规",
			value: "global_general",
			component: GlobalGeneral,
			title: "常规",
			icon: "lucide-settings",
			disabled: false,
		},
		{
			label: "用户",
			value: "global_users",
			component: GlobalUsers,
			title: "用户",
			icon: "lucide-users",
		},
		{ label: "代码", value: "global_code", component: GlobalCode, title: "全局代码", icon: "lucide-code" },
		{
			label: "重定向",
			value: "global_redirects",
			component: GlobalRedirects,
			title: "重定向",
			icon: "lucide-shuffle",
		},
		{
			label: "Robots",
			value: "global_robots",
			component: PageRobots,
			title: "Robots.txt",
			icon: "lucide-bot",
		},
		...(window.is_fc_site || window.is_developer_mode
			? [
					{
						label: "域名",
						value: "global_domains",
						component: GlobalDomains,
						title: "自定义域名",
						icon: "lucide-globe",
					},
				]
			: []),
		{
			label: "分析",
			value: "global_analytics",
			component: GlobalAnalytics,
			title: "站点分析",
			icon: "lucide-chart-bar",
		},
		{
			label: "开发者",
			value: "global_developer",
			component: GlobalDeveloper,
			title: "开发者设置",
			icon: "lucide-terminal",
		},
		{
			label: "AI",
			value: "global_ai",
			component: GlobalAI,
			title: "AI 设置",
			icon: "lucide-sparkles",
		},
	],
};

const settingsSidebarItems = [globalSettings];
if (!props.onlyGlobal) settingsSidebarItems.unshift(pageSettings);

const selectItem = (value: string) => {
	selectedItem.value = value;
	builderStore.settingsActiveTab = value;
};

// the remembered tab may not exist here (e.g. page tabs are hidden in onlyGlobal mode); fall back
// locally without persisting so the editor keeps its last page-level selection
if (!selectedItemDoc.value) {
	selectedItem.value = props.onlyGlobal ? "global_general" : "page_general";
}

provide("selectSettingsTab", selectItem);

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
