<template>
	<div class="flex min-h-full flex-col">
		<div class="sticky top-0 bg-surface-base px-3 py-3">
			<BuilderInput
				type="text"
				placeholder="Search plugins"
				:model-value="filter"
				@input="(value: string) => (filter = value)" />
		</div>

		<div class="flex flex-col px-3 pb-3">
			<CollapsibleSection section-name="Installed">
				<p v-if="!installed.length" class="text-p-sm italic text-ink-gray-5">
					{{ filter ? "Nothing here matches that." : "No plugins installed." }}
				</p>

				<div v-else class="flex flex-col">
					<ItemListRow
						v-for="plugin in installed"
						:key="plugin.name"
						class="cursor-pointer transition-none hover:bg-surface-gray-2"
						:class="!plugin.enabled && 'opacity-60'"
						role="button"
						tabindex="0"
						size="md"
						@click="open(plugin.name)"
						@keydown.enter.self="open(plugin.name)">
						<template #prefix>
							<!-- one box for any icon size. So a large icon cannot change the row height -->
							<img
								v-if="plugin.icon"
								:src="plugin.icon"
								class="size-4 shrink-0 object-contain"
								alt=""
								aria-hidden="true" />
							<span v-else class="lucide-plug size-4 shrink-0 text-ink-gray-6" aria-hidden="true" />
						</template>
						<!-- the badge is on the second line. So a label keeps the full width of the first line -->
						<div class="flex min-w-0 flex-col gap-1">
							<span class="truncate">{{ plugin.label }}</span>
							<div class="flex min-w-0 items-center gap-1.5">
								<span v-if="plugin.description" class="truncate text-xs text-ink-gray-5">
									{{ plugin.description }}
								</span>
								<Badge v-if="plugin.install_state === 'Failed'" size="sm" theme="red" label="Failed" />
								<Badge
									v-else-if="plugin.install_state === 'Installing'"
									size="sm"
									theme="blue"
									label="Installing" />
								<Tooltip v-else-if="isDevPlugin(plugin)" text="Served by a dev server in this browser tab.">
									<Badge size="sm" theme="amber" label="Dev" />
								</Tooltip>
								<!-- <Badge v-else-if="!plugin.enabled" size="sm" theme="gray" label="Disabled" /> -->
							</div>
						</div>
						<template #suffix>
							<LoadingIndicator v-if="plugin.install_state === 'Installing'" class="size-4 text-ink-gray-5" />
							<Tooltip v-else-if="isDevPlugin(plugin)" text="Stop this dev plugin">
								<Button variant="ghost" size="sm" icon="lucide-unplug" class="mr-2" @click.stop="stop" />
							</Tooltip>
							<span class="lucide-chevron-right size-4 text-ink-gray-5" aria-hidden="true" />
						</template>
					</ItemListRow>
				</div>
			</CollapsibleSection>

			<CollapsibleSection section-name="Marketplace">
				<div
					v-if="pluginsCatalog.loading && !catalog.length"
					class="flex items-center gap-2 text-p-sm text-ink-gray-5">
					<LoadingIndicator class="size-4" />
					Loading plugins…
				</div>
				<div v-else-if="pluginsCatalog.error" class="flex flex-col items-start gap-2">
					<p class="text-p-sm italic text-ink-gray-5">Could not reach the Builder Hub.</p>
					<Button variant="subtle" size="sm" label="Try again" @click="pluginsCatalog.reload()" />
				</div>
				<p v-else-if="!notInstalled.length" class="text-p-sm italic text-ink-gray-5">
					{{ emptyMarketplaceText }}
				</p>
				<ItemListRow
					v-for="plugin in notInstalled"
					:key="plugin.name"
					class="cursor-pointer transition-none hover:bg-surface-gray-2"
					role="button"
					tabindex="0"
					size="md"
					@click="open(plugin.name)"
					@keydown.enter.self="open(plugin.name)">
					<template #prefix>
						<img
							v-if="plugin.icon"
							:src="plugin.icon"
							class="size-4 shrink-0 object-contain"
							alt=""
							aria-hidden="true" />
						<span v-else class="lucide-plug size-4 shrink-0 text-ink-gray-6" aria-hidden="true" />
					</template>
					<div class="flex min-w-0 flex-col gap-1">
						<span class="truncate">{{ plugin.label }}</span>
						<span v-if="plugin.description" class="truncate text-xs text-ink-gray-5">
							{{ plugin.description }}
						</span>
					</div>
					<template #suffix>
						<span class="lucide-chevron-right size-4 text-ink-gray-5" aria-hidden="true" />
					</template>
				</ItemListRow>
			</CollapsibleSection>
		</div>

		<Button
			v-if="isDeveloperMode && canManagePlugins"
			class="mx-3 mb-3 mt-auto"
			variant="subtle"
			icon-left="lucide-plug"
			label="Load dev plugin"
			@click="showDevPluginDialog = true" />
		<DevPluginDialog />
	</div>
</template>

<script setup lang="ts">
import CollapsibleSection from "@/components/CollapsibleSection.vue";
import DevPluginDialog from "@/components/LeftPanelTabs/Plugins/DevPluginDialog.vue";
import {
	canManagePlugins,
	getPluginsCatalog,
	installations,
	promptReload,
	reloadInstallations,
	type CatalogPlugin,
} from "@/data/plugins";
import { isDevPlugin, showDevPluginDialog, stopDevPlugin } from "@/plugins/devPlugin";
import { Badge, Button, ItemListRow, LoadingIndicator, Tooltip } from "frappe-ui";
import { computed, ref } from "vue";

const emit = defineEmits<{ select: [plugin: string] }>();

const open = (plugin: string) => emit("select", plugin);

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
