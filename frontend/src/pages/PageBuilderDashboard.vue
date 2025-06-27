<template>
	<div class="flex h-screen">
		<!-- toolbar -->
		<DashboardSidebar class="z-30"></DashboardSidebar>
		<div class="flex w-full flex-1 flex-col overflow-hidden">
			<div
				class="toolbar sticky top-0 z-10 flex h-12 items-center justify-end border-b-[1px] border-outline-gray-1 bg-surface-white p-2 px-3 py-1"
				ref="toolbar">
				<router-link
					:to="{ name: 'builder', params: { pageId: 'new' } }"
					@click="
						() => {
							posthog.capture('builder_new_page_created');
						}
					">
					<BuilderButton
						variant="solid"
						iconLeft="plus"
						class="bg-surface-gray-7 !text-ink-white hover:bg-surface-gray-6">
						New
					</BuilderButton>
				</router-link>
			</div>
			<!-- Sidebar -->
			<!-- Main Content -->
			<div class="flex-1 overflow-auto">
				<section class="m-auto mb-32 flex h-fit w-3/4 max-w-6xl flex-col pt-5">
					<!-- list head -->
					<div class="sticky top-0 z-20 mb-8 flex items-center justify-between bg-surface-white px-3 py-5">
						<h1 class="text-xl font-semibold text-ink-gray-9">
							{{ builderStore.activeFolder || "All Pages" }}
						</h1>
						<div class="flex gap-2">
							<div>
								<BuilderButton
									variant="solid"
									v-show="selectionMode && selectedPages.size"
									@click="showFolderSelectorDialog = true">
									Move To Folder
								</BuilderButton>
							</div>
							<div class="relative flex" v-show="!selectionMode">
								<BuilderInput
									class="w-48"
									type="text"
									placeholder="Filter by title or route"
									v-model="searchFilter"
									autofocus
									@input="
										(value: string) => {
											searchFilter = value;
										}
									">
									<template #prefix>
										<FeatherIcon name="search" class="size-4 text-ink-gray-5"></FeatherIcon>
									</template>
								</BuilderInput>
							</div>
							<div class="max-md:hidden" v-show="!selectionMode">
								<BuilderInput
									type="select"
									class="w-24"
									v-model="typeFilter"
									:options="[
										{ label: 'All', value: '' },
										{ label: 'Draft', value: 'draft' },
										{ label: 'Published', value: 'published' },
										{ label: 'Unpublished', value: 'unpublished' },
									]" />
							</div>
							<div class="max-sm:hidden" v-show="!selectionMode">
								<BuilderInput
									type="select"
									class="w-32"
									v-model="orderBy"
									:options="[
										{ label: 'Sort', value: '', disabled: true },
										{ label: 'Last Created', value: 'creation' },
										{ label: 'Last Modified', value: 'modified' },
										{
											label: 'Alphabetically (A-Z)',
											value: 'alphabetically_a_z',
										},
										{
											label: 'Alphabetically (Z-A)',
											value: 'alphabetically_z_a',
										},
									]" />
							</div>
							<div class="max-md:hidden">
								<OptionToggle
									class="[&>div]:min-w-0"
									:options="[
										{
											label: 'Grid',
											value: 'grid',
											icon: 'grid',
											hideLabel: true,
										},
										{
											label: 'List',
											value: 'list',
											icon: 'list',
											hideLabel: true,
										},
									]"
									v-model="displayType"></OptionToggle>
							</div>
						</div>
					</div>
					<!-- pages -->
					<div>
						<div v-if="!webPages.data?.length && !searchFilter && !typeFilter" class="col-span-full">
							<p class="mt-4 px-3 text-base text-gray-500">
								You don't have any pages yet. Click on the "+ New" button to create a new page.
							</p>
						</div>
						<div v-else-if="!webPages.data?.length" class="col-span-full">
							<p class="mt-4 text-base text-gray-500">No matching pages found.</p>
						</div>
						<!-- grid -->
						<div class="grid-col grid gap-3 auto-fill-[220px]" v-if="displayType === 'grid'">
							<PageCard
								v-for="page in webPages.data"
								:selected="selectedPages.has(page.name)"
								@click.capture="($event) => handleClick($event, page)"
								:key="page.page_name"
								:page="page"
								v-on-click-and-hold="() => enableSelectionMode(page)"></PageCard>
						</div>
						<!-- list -->
						<div v-if="displayType === 'list'">
							<PageListItem
								@click.capture="($event) => handleClick($event, page)"
								v-for="page in webPages.data"
								:selected="selectedPages.has(page.name)"
								:key="page.page_name"
								:page="page"
								v-on-click-and-hold="() => enableSelectionMode(page)"></PageListItem>
						</div>
					</div>
					<BuilderButton
						class="m-auto mt-12 w-fit text-sm"
						@click="loadMore"
						v-show="webPages.hasNextPage"
						variant="subtle"
						size="sm">
						Load More
					</BuilderButton>
				</section>
			</div>
		</div>
		<SelectFolder
			v-model="showFolderSelectorDialog"
			:currentFolder="builderStore.activeFolder"
			@folderSelected="setFolder"></SelectFolder>
	</div>
</template>
<script setup lang="ts">
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import DashboardSidebar from "@/components/DashboardSidebar.vue";
import SelectFolder from "@/components/Modals/SelectFolder.vue";
import PageCard from "@/components/PageCard.vue";
import PageListItem from "@/components/PageListItem.vue";
import { webPages } from "@/data/webPage";
import vOnClickAndHold from "@/directives/vOnClickAndHold";
import useBuilderStore from "@/stores/builderStore";
import { posthog } from "@/telemetry";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { useDark, useEventListener, useStorage, useToggle, watchDebounced } from "@vueuse/core";
import { createResource } from "frappe-ui";
import { onActivated, Ref, ref, watch } from "vue";

const isDark = useDark({
	attribute: "data-theme",
});
const toggleDark = useToggle(isDark);
const builderStore = useBuilderStore();
const displayType = useStorage("displayType", "grid") as Ref<"grid" | "list">;
const showFolderSelectorDialog = ref(false);

const searchFilter = ref("");
const typeFilter = ref("");
const orderBy = useStorage("orderBy", "creation") as Ref<
	"creation" | "modified" | "alphabetically_a_z" | "alphabetically_z_a"
>;

const orderMap = {
	creation: "creation desc",
	modified: "modified desc",
	alphabetically_a_z: "page_title asc",
	alphabetically_z_a: "page_title desc",
};

const selectedPages = ref(new Set<string>());
const selectionMode = ref(false);

onActivated(() => {
	posthog.capture("builder_dashboard_page_visited");
});

watch(
	() => builderStore.activeFolder,
	() => fetchPages(),
);

// remove selection mode when the escape key is pressed
useEventListener(document, "keydown", (ev) => {
	if (ev.key === "Escape") {
		selectedPages.value.clear();
		selectionMode.value = false;
	}
});

const fetchPages = () => {
	const filters = {
		is_template: 0,
	} as any;
	if (typeFilter.value) {
		if (typeFilter.value === "published") {
			filters["published"] = true;
		} else if (typeFilter.value === "unpublished") {
			filters["published"] = false;
		} else if (typeFilter.value === "draft") {
			filters["draft_blocks"] = ["is", "set"];
		}
	}
	const orFilters = {} as any;
	if (searchFilter.value) {
		orFilters["page_title"] = ["like", `%${searchFilter.value}%`];
		orFilters["route"] = ["like", `%${searchFilter.value}%`];
	}
	if (builderStore.activeFolder) {
		filters["project_folder"] = builderStore.activeFolder;
	}

	webPages.update({
		filters,
		orFilters,
		orderBy: orderMap[orderBy.value],
	});
	webPages.fetch();
};

const loadMore = () => {
	webPages.next();
};

const firstHold = ref(false);

const handleClick = (e: MouseEvent, page: BuilderPage) => {
	if (selectionMode.value) {
		e.preventDefault();
		e.stopPropagation();
		if (firstHold.value) {
			firstHold.value = false;
			return;
		}
		if (e.shiftKey) {
			const pages = webPages.data || [];
			// select all pages between the last selected page and the current page
			const lastSelectedPage = selectedPages.value.size
				? pages.find((p: BuilderPage) => p.name === Array.from(selectedPages.value)[0])
				: null;
			if (lastSelectedPage) {
				const lastSelectedPageIndex = pages.indexOf(lastSelectedPage);
				const currentPageIndex = pages.indexOf(page);
				const start = Math.min(lastSelectedPageIndex, currentPageIndex);
				const end = Math.max(lastSelectedPageIndex, currentPageIndex);
				for (let i = start; i <= end; i++) {
					const p = pages[i];
					selectedPages.value.add(p.name);
				}
			}
		} else if (e.ctrlKey || e.metaKey) {
			togglePageSelection(page);
		} else {
			selectedPages.value.clear();
			togglePageSelection(page);
		}
	} else {
		posthog.capture("builder_page_opened", { page_name: page.page_name });
	}
};

const enableSelectionMode = (page: BuilderPage) => {
	selectionMode.value = true;
	firstHold.value = true;
	togglePageSelection(page);
};

const togglePageSelection = (page: BuilderPage) => {
	if (selectedPages.value.has(page.name)) {
		selectedPages.value.delete(page.name);
	} else {
		selectedPages.value.add(page.name);
	}
	// Disable selection mode if no pages are selected
	if (!selectedPages.value.size) {
		selectionMode.value = false;
	}
};

watchDebounced([searchFilter, typeFilter, orderBy], fetchPages, {
	debounce: 300,
	immediate: true,
});

const setFolder = async (folder: string) => {
	createResource({
		method: "POST",
		url: "builder.api.update_page_folder",
	})
		.submit({
			pages: Array.from(selectedPages.value),
			folder_name: folder,
		})
		.then(() => {
			for (const pageName of selectedPages.value) {
				const page = webPages.data?.find((p: BuilderPage) => p.name === pageName);
				if (page) {
					page.project_folder = folder;
				}
			}
			selectedPages.value.clear();
			selectionMode.value = false;
			showFolderSelectorDialog.value = false;
			builderStore.activeFolder = folder;
		});
};

const showSettingsDialog = ref(false);
</script>
