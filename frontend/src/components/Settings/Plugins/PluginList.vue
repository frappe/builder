<template>
	<!-- laid out as the Users pane: search and the main action, then a list per section -->
	<div class="flex flex-col gap-5">
		<div class="flex items-center justify-between gap-2">
			<BuilderInput
				type="text"
				class="w-72"
				placeholder="Search plugins"
				icon-left="lucide-search"
				:model-value="filter"
				@input="(value: string) => (filter = value)" />
			<div class="flex items-center gap-2">
				<Button
					icon="lucide-power"
					aria-label="Turn off plugins"
					tooltip="Turn off plugins"
					@click="setPluginsDisabled(true)" />
				<Button
					v-if="isDeveloperMode && canManagePlugins"
					variant="solid"
					icon-left="lucide-plug"
					label="Load dev plugin"
					@click="showDevPluginDialog = true" />
			</div>
		</div>

		<div class="flex flex-col">
			<span class="sticky top-0 z-10 bg-surface-base pb-1 text-p-sm text-ink-gray-5">
				Installed ({{ installed.length }})
			</span>
			<div
				v-for="plugin in installed"
				:key="plugin.name"
				class="flex cursor-pointer items-center gap-2 rounded-4 border-b border-outline-gray-1 px-2 py-2 last:border-b-0 hover:bg-surface-gray-1"
				:class="!plugin.enabled && 'opacity-60'"
				role="button"
				tabindex="0"
				@click="open(plugin.name)"
				@keydown.enter.self="open(plugin.name)">
				<PluginIcon :icon="plugin.icon" />
				<div class="flex min-w-0 flex-col">
					<span class="truncate text-p-sm text-ink-gray-8">{{ plugin.label }}</span>
					<span v-if="plugin.description" class="truncate text-p-xs text-ink-gray-5">
						{{ plugin.description }}
					</span>
				</div>
				<div class="ml-auto flex shrink-0 items-center gap-1">
					<Badge v-if="plugin.install_state === 'Failed'" theme="red" label="Failed" />
					<template v-else-if="plugin.install_state === 'Installing'">
						<Badge theme="blue" label="Installing" />
						<LoadingIndicator class="size-4 text-ink-gray-5" />
					</template>
					<template v-else-if="isDevPlugin(plugin)">
						<Tooltip text="Served by a dev server in this browser tab.">
							<Badge theme="amber" label="Dev" />
						</Tooltip>
						<Tooltip text="Stop this dev plugin">
							<Button variant="ghost" size="sm" icon="lucide-unplug" @click.stop="stop" />
						</Tooltip>
					</template>
					<span class="lucide-chevron-right size-4 text-ink-gray-5" aria-hidden="true" />
				</div>
			</div>
			<div v-if="!installed.length" class="py-6 text-center text-p-sm text-ink-gray-5">
				{{ filter ? "Nothing here matches that." : "No plugins installed." }}
			</div>
			<div
				v-if="isBuildWithBobShown && canManagePlugins && builderStore.isAIEnabled && !filter"
				class="flex cursor-pointer items-center gap-2 rounded-4 px-2 py-2 hover:bg-surface-gray-1"
				role="button"
				tabindex="0"
				@click="buildWithBob"
				@keydown.enter.self="buildWithBob">
				<PluginIcon icon="lucide-sparkle" />
				<span class="truncate text-p-sm text-ink-gray-6">Build one with Bob</span>
			</div>
		</div>

		<!-- the catalog comes from the Builder Hub. Another Hub is set by builder_hub_url in the site config -->
		<!-- an unreachable Hub is nothing the user can fix, so the section goes rather than say so -->
		<div v-if="!pluginsCatalog.error" class="flex flex-col">
			<span class="sticky top-0 z-10 bg-surface-base pb-1 text-p-sm text-ink-gray-5">
				Marketplace ({{ notInstalled.length }})
			</span>
			<div
				v-if="pluginsCatalog.loading && !catalog.length"
				class="flex items-center justify-center gap-2 py-6 text-p-sm text-ink-gray-5">
				<LoadingIndicator class="size-4" />
				Loading plugins…
			</div>
			<div v-else-if="!notInstalled.length" class="py-6 text-center text-p-sm text-ink-gray-5">
				{{ emptyMarketplaceText }}
			</div>
			<div
				v-for="plugin in notInstalled"
				:key="plugin.name"
				class="flex cursor-pointer items-center gap-2 rounded-4 border-b border-outline-gray-1 px-2 py-2 last:border-b-0 hover:bg-surface-gray-1"
				role="button"
				tabindex="0"
				@click="open(plugin.name)"
				@keydown.enter.self="open(plugin.name)">
				<PluginIcon :icon="plugin.icon" />
				<div class="flex min-w-0 flex-col">
					<span class="truncate text-p-sm text-ink-gray-8">{{ plugin.label }}</span>
					<span v-if="plugin.description" class="truncate text-p-xs text-ink-gray-5">
						{{ plugin.description }}
					</span>
				</div>
				<span class="lucide-chevron-right ml-auto size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
			</div>
		</div>
		<DevPluginDialog />
	</div>
</template>

<script setup lang="ts">
import DevPluginDialog from "@/components/Settings/Plugins/DevPluginDialog.vue";
import PluginIcon from "@/components/Settings/Plugins/PluginIcon.vue";
import {
	canManagePlugins,
	getPluginsCatalog,
	installations,
	promptReload,
	reloadInstallations,
	setPluginsDisabled,
	type CatalogPlugin,
} from "@/data/plugins";
import { isDevPlugin, showDevPluginDialog, stopDevPlugin } from "@/plugins/devPlugin";
import useBuilderStore from "@/stores/builderStore";
import { Badge, Button, LoadingIndicator, Tooltip } from "frappe-ui";
import { computed, ref } from "vue";

const emit = defineEmits<{ select: [plugin: string] }>();

const open = (plugin: string) => emit("select", plugin);

const builderStore = useBuilderStore();

/** Off for now. Set it to true to show "Build one with Bob" again. */
const isBuildWithBobShown = false;

/** Opens Bob with the sentence started, so the user only says what the tool does. */
const buildWithBob = () => {
	builderStore.leftPanelActiveTab = "Chat";
	builderStore.aiPromptDraft = "Build an editor plugin that ";
};

const stop = async () => {
	await stopDevPlugin();
	await reloadInstallations();
	promptReload("Dev plugin stopped");
};

// a dev load runs code that the site did not install. So only a developer sees the button
const isDeveloperMode = Boolean(window.is_developer_mode);

const filter = ref("");

/** An empty search matches all plugins. Other searches look in the label, the description and the package name. */
function matchesFilter(plugin: CatalogPlugin) {
	const wanted = filter.value.trim().toLowerCase();
	if (!wanted) return true;
	return `${plugin.label} ${plugin.description ?? ""} ${plugin.name}`.toLowerCase().includes(wanted);
}

const installed = computed(() => installations.value.filter(matchesFilter));

const pluginsCatalog = getPluginsCatalog();
const catalog = computed<CatalogPlugin[]>(() => pluginsCatalog.data?.plugins ?? []);

/** The catalog entries that are not installed yet. */
const notInstalled = computed<CatalogPlugin[]>(() => {
	const installedNames = new Set(installations.value.map((plugin) => plugin.name));
	return catalog.value.filter((plugin) => !installedNames.has(plugin.name) && matchesFilter(plugin));
});

/** The Hub answered. So an empty section means a search with no match, all plugins installed, or an empty Hub. */
const emptyMarketplaceText = computed(() => {
	if (filter.value) return "Nothing here matches that.";
	if (catalog.value.length) return "You have installed every plugin on the Hub.";
	return "The Hub has no plugins yet.";
});
</script>
