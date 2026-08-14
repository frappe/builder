<template>
	<div class="flex h-[88vh] max-h-[800px] overflow-hidden">
		<div class="flex w-48 shrink-0 flex-col gap-5 bg-surface-gray-1 p-4 px-2">
			<span class="text-lg-semibold px-2 text-ink-gray-9">{{ __("Settings") }}</span>
			<div class="flex flex-col gap-0.5" v-for="group in visibleGroups" :key="group.title">
				<span class="text-base-medium mb-2 px-2 text-ink-gray-5">
					{{ group.title }}
				</span>
				<Button
					v-for="link in group.items"
					:key="link.name"
					:variant="selectedItem === link.name ? 'subtle' : 'ghost'"
					:disabled="link.disabled"
					:icon-left="link.icon"
					@click="!link.disabled && selectItem(link.name)"
					:class="{
						'!bg-surface-gray-3': selectedItem === link.name,
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
				<span class="text-ink-gray-5">{{ __("Loading...") }}</span>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import { settingsGroupLabels, settingsGroups, settingsItems } from "@/components/Settings";
import builderProjectFolder from "@/data/builderProjectFolder";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { __ } from "@/translation";
import { computed, onActivated, onMounted, provide, ref, watch } from "vue";
import { useRoute } from "vue-router";

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

const visibleGroups = computed(() =>
	settingsGroups
		.filter((group) => !(props.onlyGlobal && group === "Current Page"))
		.map((group) => ({
			title: settingsGroupLabels[group],
			items: settingsItems.visible.value.filter((item) => item.group === group),
		}))
		.filter((group) => group.items.length),
);

const selectedItemDoc = computed(() =>
	visibleGroups.value.flatMap((group) => group.items).find((item) => item.name === selectedItem.value),
);

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
