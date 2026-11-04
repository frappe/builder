<template>
	<div class="flex">
		<PanelResizer
			:dimension="builderStore.builderLayout.leftPanelWidth"
			side="right"
			:minDimension="minWidth"
			:maxDimension="500"
			@resize="(width) => (builderStore.builderLayout.leftPanelWidth = width)" />
		<div
			class="flex min-h-full flex-col items-center gap-2 border-r border-outline-gray-1 p-3"
			ref="miniSidebar">
			<template v-for="tab of barTabs" :key="tab.name">
				<div v-if="tab.name === firstPluginTab" class="w-6 border-t border-outline-gray-2" role="separator" />
				<Tooltip side="right">
					<template #content>
						<span class="flex items-center gap-1.5">
							{{ tab.label }}
							<KeyboardShortcut v-if="tab.shortcut" :combo="tab.shortcut" class="!text-xs !text-ink-gray-4" />
						</span>
					</template>
					<span class="relative inline-flex" @contextmenu="tab.plugin && openTabMenu($event, tab)">
						<Button
							:icon="tab.icon"
							size="md"
							:class="{ '!text-ink-gray-6': !isActive(tab) }"
							:variant="isActive(tab) ? 'subtle' : 'ghost'"
							@click.stop="select(tab)"></Button>
						<!-- a tab a plugin added while the editor ran, until the user opens it -->
						<span
							v-if="unseenTabs.has(tab.name)"
							class="pointer-events-none absolute right-1 top-1 size-2 animate-pulse rounded-full bg-surface-blue-6" />
					</span>
				</Tooltip>
			</template>
		</div>
		<ContextMenu ref="tabMenu" :options="tabMenuOptions" :context="menuTab" />
		<div
			class="no-scrollbar relative min-h-full overflow-auto"
			:style="{
				width: `${builderStore.builderLayout.leftPanelWidth}px`,
			}">
			<template v-for="tab of tabs" :key="tab.name">
				<div
					v-if="tab.component && mountedTabs.has(tab.name)"
					v-show="builderStore.leftPanelActiveTab === tab.name"
					class="h-full">
					<component :is="tab.component" v-bind="tab.props?.()" />
				</div>
			</template>
		</div>

		<TokenManager
			v-model="builderStore.showTokenManager"
			:container="miniSidebar"
			:readonly="Boolean(editorDemo)" />
	</div>
</template>
<script setup lang="ts">
import ContextMenu from "@/components/ContextMenu.vue";
import { leftPanelTabs, type LeftPanelTab } from "@/components/LeftPanelTabs";
import { hiddenPluginTabs, setPluginTabHidden, unseenTabs } from "@/data/plugins";
import TokenManager from "@/components/Modals/TokenManager.vue";
import { __ } from "@/translation";
import { editorDemo } from "@/utils/editorDemo";
import useBuilderStore from "@/stores/builderStore";
import { KeyboardShortcut, Tooltip, useKeyboardShortcut } from "frappe-ui";
import { computed, reactive, Ref, ref, watch, watchEffect } from "vue";
import { useRoute } from "vue-router";
import PanelResizer from "./PanelResizer.vue";

const builderStore = useBuilderStore();
const route = useRoute();

const tabs = leftPanelTabs.visible;

const PANEL_MIN_WIDTH = 200;
const activeTab = computed(() => tabs.value.find((tab) => tab.name === builderStore.leftPanelActiveTab));
const minWidth = computed(() => Math.max(PANEL_MIN_WIDTH, activeTab.value?.minWidth ?? 0));

// widen the stored width rather than only the drawn one: the canvas is laid out from it
watch(
	minWidth,
	(min) => {
		if (builderStore.builderLayout.leftPanelWidth < min) builderStore.builderLayout.leftPanelWidth = min;
	},
	{ immediate: true },
);

const miniSidebar = ref(null) as Ref<HTMLElement | null>;
const mountedTabs = reactive(new Set<string>());

const isActive = (tab: LeftPanelTab) => tab.isActive?.() ?? builderStore.leftPanelActiveTab === tab.name;

// plugin tabs sit below the editor's own; a hidden one still shows while open, so Open has somewhere to land
const pluginTabs = computed(() =>
	tabs.value.filter((tab) => tab.plugin && (!hiddenPluginTabs.value.has(tab.plugin) || isActive(tab))),
);
const barTabs = computed(() => [...tabs.value.filter((tab) => !tab.plugin), ...pluginTabs.value]);
const firstPluginTab = computed(() => pluginTabs.value[0]?.name);

const tabMenu = ref<InstanceType<typeof ContextMenu> | null>(null);
const menuTab = ref<LeftPanelTab | null>(null);
const tabMenuOptions = [
	{ label: __("Hide from left bar"), action: (tab: LeftPanelTab) => setPluginTabHidden(tab.plugin!, true) },
];
const openTabMenu = (event: MouseEvent, tab: LeftPanelTab) => {
	menuTab.value = tab;
	tabMenu.value?.show(event);
};

watch(
	() => builderStore.leftPanelActiveTab,
	(tab) => unseenTabs.delete(tab),
);

const select = (tab: LeftPanelTab) => {
	if (tab.action) return tab.action();
	builderStore.leftPanelActiveTab = tab.name;
	builderStore.showTokenManager = false;
};

// read once at setup, so a tab registered later gets no binding until reload
useKeyboardShortcut(
	tabs.value
		.filter((tab) => tab.shortcut)
		.map((tab) => ({
			combo: tab.shortcut!,
			description: `Show ${tab.label} Panel`,
			group: "View",
			handler: () => select(tab),
		})),
);

// a non-lazy tab mounts as soon as it registers, a lazy one on first open
watchEffect(() => {
	tabs.value.forEach((tab) => {
		if (!tab.component) return;
		if (!tab.lazy || builderStore.leftPanelActiveTab === tab.name || tab.preload?.()) {
			mountedTabs.add(tab.name);
		}
	});
});

watch(
	() => route.fullPath,
	() => {
		builderStore.showTokenManager = false;
	},
);
</script>
