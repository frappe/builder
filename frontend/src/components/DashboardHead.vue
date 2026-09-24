<template>
	<div class="m-auto flex w-3/4 max-w-6xl items-center justify-between bg-surface-base px-3.5 py-5 pt-8">
		<h1 class="text-xl-semibold flex min-w-0 items-center gap-1.5 text-ink-gray-9">
			<span
				v-if="dashboardView === 'folder' && !searchFilter"
				class="lucide-folder size-5 shrink-0 text-ink-gray-5"
				aria-hidden="true" />
			<span class="truncate" :title="title">{{ title }}</span>
		</h1>
		<div class="flex shrink-0 gap-2">
			<div class="max-md:hidden" v-show="displayType !== 'tree'">
				<Select
					v-model="statusFilter"
					:options="[
						{ label: __('Status'), value: '', disabled: true },
						{ label: __('All'), value: 'all' },
						{ label: __('Live'), value: 'live' },
						{ label: __('Staging'), value: 'staging' },
						{ label: __('Draft'), value: 'draft' },
					]" />
			</div>
			<div v-if="displayType === 'tree'">
				<Button
					variant="subtle"
					size="sm"
					class="w-20"
					@click="
						treeExpanded
							? (collapseTreeFn?.(), (treeExpanded = false))
							: (expandTreeFn?.(), (treeExpanded = true))
					">
					{{ treeExpanded ? __("Collapse") : __("Expand") }}
				</Button>
			</div>
			<div class="max-sm:hidden" v-show="displayType !== 'tree'">
				<Select
					v-model="orderBy"
					:options="[
						{ label: __('Sort'), value: '', disabled: true },
						{ label: __('Last Created'), value: 'creation' },
						{ label: __('Last Modified'), value: 'modified' },
						{
							label: __('Alphabetically (A-Z)'),
							value: 'alphabetically_a_z',
						},
						{
							label: __('Alphabetically (Z-A)'),
							value: 'alphabetically_z_a',
						},
					]" />
			</div>
			<div class="max-md:hidden">
				<OptionToggle
					class="[&>div]:min-w-0"
					:options="[
						{
							label: __('Grid'),
							value: 'grid',
							icon: 'lucide-grid-2x2',
							hideLabel: true,
						},
						{
							label: __('List'),
							value: 'list',
							icon: 'lucide-list',
							hideLabel: true,
						},
						{
							label: __('Route Tree'),
							value: 'tree',
							icon: ListTreeIcon,
							hideLabel: true,
						},
					]"
					v-model="displayType"></OptionToggle>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import { useDashboardState } from "@/composables/useDashboardState";
import useBuilderStore from "@/stores/builderStore";
import { Button, Select } from "frappe-ui";
import { computed } from "vue";
import ListTreeIcon from "~icons/lucide/list-tree";

const builderStore = useBuilderStore();
const {
	searchFilter,
	treeExpanded,
	displayType,
	statusFilter,
	orderBy,
	expandTreeFn,
	collapseTreeFn,
	dashboardView,
} = useDashboardState();

const viewTitles = {
	all: __("All Pages"),
};

const title = computed(() => {
	if (searchFilter.value) return __("Results for “{0}”", [searchFilter.value]);
	if (dashboardView.value === "folder") return builderStore.activeFolder;
	return viewTitles[dashboardView.value];
});
</script>
