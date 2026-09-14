<template>
	<div class="flex min-h-full flex-col">
		<div class="sticky top-0 bg-surface-base px-3 py-3">
			<BuilderInput
				type="text"
				placeholder="Search extensions"
				:model-value="filter"
				@input="(value: string) => (filter = value)" />
		</div>

		<div class="flex flex-col px-3 pb-3">
			<CollapsibleSection section-name="Installed">
				<p v-if="!installed.length" class="text-p-sm italic text-ink-gray-5">
					{{ filter ? "Nothing here matches that." : "No extensions installed." }}
				</p>

				<div v-else class="flex flex-col">
					<ItemListRow
						v-for="extension in installed"
						:key="extension.name"
						class="cursor-pointer transition-none hover:bg-surface-gray-2"
						:class="!extension.enabled && 'opacity-60'"
						role="button"
						tabindex="0"
						size="md"
						@click="open(extension.name, true)"
						@keydown.enter.self="open(extension.name, true)">
						<template #prefix>
							<!-- one box whatever the file measures, so a stray icon cannot set the row height -->
							<img
								v-if="extension.icon"
								:src="extension.icon"
								class="size-4 shrink-0 object-contain"
								alt=""
								aria-hidden="true" />
							<span v-else class="lucide-plug size-4 shrink-0 text-ink-gray-6" aria-hidden="true" />
						</template>
						<!-- The badge sits on the second line, so a label keeps the width of the first. -->
						<div class="flex min-w-0 flex-col gap-1">
							<span class="truncate">{{ extension.label }}</span>
							<div class="flex min-w-0 items-center gap-1.5">
								<span v-if="extension.description" class="truncate text-xs text-ink-gray-5">
									{{ extension.description }}
								</span>
								<Badge v-if="extension.install_state === 'Failed'" size="sm" theme="red" label="Failed" />
								<Badge
									v-else-if="extension.install_state === 'Installing'"
									size="sm"
									theme="blue"
									label="Installing" />
								<Tooltip
									v-else-if="isDevExtension(extension)"
									text="Served by a dev server. A reload drops it.">
									<Badge size="sm" theme="orange" label="Dev" />
								</Tooltip>
								<!-- <Badge v-else-if="!extension.enabled" size="sm" theme="gray" label="Disabled" /> -->
							</div>
						</div>
						<template #suffix>
							<LoadingIndicator
								v-if="extension.install_state === 'Installing'"
								class="size-4 text-ink-gray-5" />
							<Tooltip v-else-if="isDevExtension(extension)" text="Stop this dev extension">
								<Button
									variant="ghost"
									size="sm"
									icon="lucide-unplug"
									class="mr-2"
									@click.stop="stopDevExtension()" />
							</Tooltip>
							<span class="lucide-chevron-right size-4 text-ink-gray-5" aria-hidden="true" />
						</template>
					</ItemListRow>
				</div>
			</CollapsibleSection>

			<CollapsibleSection section-name="Marketplace">
				<div
					v-if="extensionsCatalog.loading && !catalog.length"
					class="flex items-center gap-2 text-p-sm text-ink-gray-5">
					<LoadingIndicator class="size-4" />
					Loading extensions…
				</div>
				<div v-else-if="extensionsCatalog.error" class="flex flex-col items-start gap-2">
					<p class="text-p-sm italic text-ink-gray-5">Could not reach the Builder Hub.</p>
					<Button variant="subtle" size="sm" label="Try again" @click="extensionsCatalog.reload()" />
				</div>
				<p v-else-if="!notInstalled.length" class="text-p-sm italic text-ink-gray-5">
					{{ emptyMarketplaceText }}
				</p>
				<ItemListRow
					v-for="extension in notInstalled"
					:key="extension.name"
					class="cursor-pointer transition-none hover:bg-surface-gray-2"
					role="button"
					tabindex="0"
					size="md"
					@click="open(extension.name, false)"
					@keydown.enter.self="open(extension.name, false)">
					<template #prefix>
						<img
							v-if="extension.icon"
							:src="extension.icon"
							class="size-4 shrink-0 object-contain"
							alt=""
							aria-hidden="true" />
						<span v-else class="lucide-plug size-4 shrink-0 text-ink-gray-6" aria-hidden="true" />
					</template>
					<div class="flex min-w-0 flex-col gap-1">
						<span class="truncate">{{ extension.label }}</span>
						<span v-if="extension.description" class="truncate text-xs text-ink-gray-5">
							{{ extension.description }}
						</span>
					</div>
					<template #suffix>
						<span class="lucide-chevron-right size-4 text-ink-gray-5" aria-hidden="true" />
					</template>
				</ItemListRow>
			</CollapsibleSection>
		</div>

		<Button
			v-if="isDeveloperMode"
			class="mx-3 mb-3 mt-auto"
			variant="subtle"
			icon-left="lucide-plug"
			label="Load dev extension"
			@click="showDevExtensionDialog = true" />
	</div>
</template>

<script setup lang="ts">
import CollapsibleSection from "@/components/CollapsibleSection.vue";
import {
	userInstallations,
	getExtensionsCatalog,
	CatalogExtension,
	SelectedExtension,
} from "@/data/extensions";
import { isDevExtension, showDevExtensionDialog, stopDevExtension } from "@/extensions/devExtension";
import { Badge, Button, ItemListRow, LoadingIndicator, Tooltip } from "frappe-ui";
import { computed, ref } from "vue";

const emit = defineEmits<{ select: [selection: SelectedExtension] }>();

const open = (name: string, isInstalled: boolean) => emit("select", { name, isInstalled });

// loading one runs code the editor never installed, so only a developer sees the button
const isDeveloperMode = Boolean(window.is_developer_mode);

const filter = ref("");

/** Empty search matches everything; otherwise the label, description, and package name are searched. */
function matchesFilter(extension: CatalogExtension) {
	const wanted = filter.value.trim().toLowerCase();
	if (!wanted) return true;
	return `${extension.label} ${extension.description ?? ""} ${extension.name}`.toLowerCase().includes(wanted);
}

const installed = computed(() => userInstallations.value.filter(matchesFilter));

const extensionsCatalog = getExtensionsCatalog();
const catalog = computed<CatalogExtension[]>(() => extensionsCatalog.data?.extensions ?? []);

/** Catalog entries this user has not installed yet. */
const notInstalled = computed<CatalogExtension[]>(() => {
	const installedNames = new Set(userInstallations.value.map((extension) => extension.name));
	return catalog.value.filter((extension) => !installedNames.has(extension.name) && matchesFilter(extension));
});

/** The Hub answered, so an empty section means a search, a full install, or an empty Hub. */
const emptyMarketplaceText = computed(() => {
	if (filter.value) return "Nothing here matches that.";
	if (catalog.value.length) return "You have installed every extension on the Hub.";
	return "The Hub has no extensions yet.";
});
</script>
