<template>
	<div class="flex">
		<PanelResizer
			:dimension="builderStore.builderLayout.leftPanelWidth"
			side="right"
			:minDimension="200"
			:maxDimension="500"
			@resize="(width) => (builderStore.builderLayout.leftPanelWidth = width)" />
		<div
			class="flex min-h-full flex-col items-center gap-2 border-r border-outline-gray-1 p-3"
			ref="miniSidebar">
			<Tooltip v-for="tab of tabs" :key="tab.name" :text="tabLabel(tab)" placement="right">
				<Button
					:icon="tab.icon"
					size="md"
					:class="{ '!text-ink-gray-6': !isActive(tab) }"
					:variant="isActive(tab) ? 'subtle' : 'ghost'"
					@click.stop="select(tab)"></Button>
			</Tooltip>
		</div>
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

		<TokenManager v-model="builderStore.showTokenManager" :container="miniSidebar" />
	</div>
</template>
<script setup lang="ts">
import { leftPanelTabs, type LeftPanelTab } from "@/components/LeftPanelTabs";
import TokenManager from "@/components/Modals/TokenManager.vue";
import useBuilderStore from "@/stores/builderStore";
import { formatShortcutLabel, Tooltip, useShortcut } from "frappe-ui";
import { reactive, Ref, ref, watch, watchEffect } from "vue";
import { useRoute } from "vue-router";
import PanelResizer from "./PanelResizer.vue";

const builderStore = useBuilderStore();
const route = useRoute();

const tabs = leftPanelTabs.visible;

const miniSidebar = ref(null) as Ref<HTMLElement | null>;
const mountedTabs = reactive(new Set<string>());

const isActive = (tab: LeftPanelTab) => tab.isActive?.() ?? builderStore.leftPanelActiveTab === tab.name;

const select = (tab: LeftPanelTab) => {
	if (tab.action) return tab.action();
	builderStore.leftPanelActiveTab = tab.name;
	builderStore.showTokenManager = false;
};

const tabLabel = (tab: LeftPanelTab) =>
	tab.shortcut ? `${tab.label} (${formatShortcutLabel(tab.shortcut)})` : tab.label;

// read once at setup, so a tab registered later gets no binding until reload
useShortcut(
	tabs.value
		.filter((tab) => tab.shortcut)
		.map((tab) => ({
			...tab.shortcut!,
			description: `Show ${tab.label} panel`,
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
