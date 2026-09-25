<template>
	<div class="no-scrollbar flex-1 overflow-auto">
		<section class="m-auto mb-24 flex h-fit w-3/4 max-w-6xl flex-col pt-5">
			<!-- pages -->
			<div>
				<p v-if="showsEmptyState && dashboardView === 'folder'" class="px-3 text-base text-ink-gray-5">
					{{ __("No pages in this folder yet.") }}
				</p>
				<div v-else-if="showsEmptyState" class="col-span-full">
					<p class="px-3 text-base text-gray-500">
						{{ __("You don't have any pages yet. Click on the + New button to create a new page.") }}
					</p>
				</div>
				<div v-else-if="!webPages.data?.length" class="col-span-full">
					<p class="px-3 text-base text-gray-500">{{ __("No matching pages found.") }}</p>
				</div>
				<!-- grid -->
				<div class="grid-col grid gap-3 auto-fill-[210px]" v-if="displayType === 'grid'">
					<PageCard
						v-for="page in webPages.data"
						:key="page.page_name"
						@click.capture="handleClick(page)"
						:page="page"></PageCard>
				</div>
				<!-- list -->
				<div v-if="displayType === 'list'">
					<PageListItem
						v-for="page in webPages.data"
						:key="page.page_name"
						@click.capture="handleClick(page)"
						:page="page"></PageListItem>
				</div>
				<!-- tree -->
				<div v-if="displayType === 'tree' && !showsEmptyState">
					<RouteTreeView
						ref="routeTreeRef"
						class="pl-2 pr-3"
						:search-filter="searchFilter"
						:active-folder="searchFilter ? '' : builderStore.activeFolder" />
				</div>
			</div>
			<Button
				class="m-auto mt-12 w-fit text-sm"
				@click="loadMore"
				v-if="webPages.data?.length && webPages.hasNextPage && displayType !== 'tree'"
				variant="subtle"
				size="sm">
				{{ __("Load More") }}
			</Button>
		</section>
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import PageCard from "@/components/PageCard.vue";
import PageListItem from "@/components/PageListItem.vue";
import RouteTreeView from "@/components/RouteTreeView.vue";
import { useDashboardState } from "@/composables/useDashboardState";
import { pagesWithUnpublishedChanges, webPages } from "@/data/webPage";
import useBuilderStore from "@/stores/builderStore";
import { BuilderPage } from "@/types/doctypes";
import { watchDebounced } from "@vueuse/core";
import { useTelemetry } from "@framework/ui/telemetry";
import { computed, onActivated, onDeactivated, onMounted, onUnmounted, ref, watch } from "vue";

const routeTreeRef = ref<InstanceType<typeof RouteTreeView>>();

const { capture } = useTelemetry();
const builderStore = useBuilderStore();
const { searchFilter, statusFilter, orderBy, displayType, expandTreeFn, collapseTreeFn, dashboardView } =
	useDashboardState();

onActivated(() => {
	builderStore.realtime.doctype_subscribe("Builder Page");
	builderStore.realtime.on("list_update", (e) => {
		if (e.doctype !== "Builder Page") return;
		fetchPages();
		pagesWithUnpublishedChanges.fetch();
	});
	// publishing is the only thing that moves this set, so it skips the list's filters
	pagesWithUnpublishedChanges.fetch();
});

onDeactivated(() => {
	builderStore.realtime.doctype_unsubscribe("Builder Page");
});

onMounted(() => {
	expandTreeFn.value = () => routeTreeRef.value?.expandAll();
	collapseTreeFn.value = () => routeTreeRef.value?.collapseAll();
});

onUnmounted(() => {
	expandTreeFn.value = null;
	collapseTreeFn.value = null;
});

const hasNoPages = computed(() => !webPages.loading && Array.isArray(webPages.data) && !webPages.data.length);
const filteringByStatus = computed(() => Boolean(statusFilter.value) && statusFilter.value !== "all");
// the tree has its own "no pages" line, so it steps aside while the empty message shows
const showsEmptyState = computed(() => hasNoPages.value && !searchFilter.value && !filteringByStatus.value);

const orderMap = {
	creation: "creation desc",
	modified: "modified desc",
	alphabetically_a_z: "page_title asc",
	alphabetically_z_a: "page_title desc",
};

let freshlyMounted = true;
onActivated(() => {
	capture("builder_dashboard_page_visited");
	// the dashboard is kept alive — refresh the list when returning to it so
	// pages created elsewhere (e.g. from a template) show up without a reload
	if (!freshlyMounted) {
		fetchPages();
	}
	freshlyMounted = false;
});

watch(
	() => builderStore.activeFolder,
	() => fetchPages(),
);

watch([displayType, dashboardView], () => fetchPages());

const statusFilters = {
	live: { published: 1 },
	staging: { staging: 1 },
	draft: { published: 0, staging: 0 },
};

const fetchPages = () => {
	const filters = {
		is_template: 0,
	} as any;
	if (displayType.value !== "tree") {
		Object.assign(filters, statusFilters[statusFilter.value as keyof typeof statusFilters]);
	}
	const orFilters = {} as any;
	if (searchFilter.value) {
		orFilters["page_title"] = ["like", `%${searchFilter.value}%`];
		orFilters["route"] = ["like", `%${searchFilter.value}%`];
	}
	// search looks across every page, the views only narrow an unsearched list
	if (!searchFilter.value) Object.assign(filters, viewFilters());

	webPages.update({
		filters,
		orFilters,
		orderBy: orderMap[orderBy.value],
	});
	webPages.fetch();
};

function viewFilters() {
	if (dashboardView.value === "folder") return { project_folder: builderStore.activeFolder };
	return {};
}

const loadMore = () => {
	webPages.next();
};

const handleClick = (page: BuilderPage) => {
	capture("builder_page_opened", { page_name: page.page_name });
};

watchDebounced([searchFilter, statusFilter, orderBy], fetchPages, {
	debounce: 300,
	immediate: true,
});
</script>
