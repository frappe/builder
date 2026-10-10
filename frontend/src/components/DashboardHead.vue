<template>
	<div
		class="m-auto flex w-3/4 max-w-6xl flex-wrap items-center justify-between gap-x-4 gap-y-3 bg-surface-base px-3.5 py-5 pt-8">
		<h1
			class="text-xl-semibold truncate text-ink-gray-9"
			:title="builderStore.activeFolder || __('All Pages')">
			{{ builderStore.activeFolder || __("All Pages") }}
		</h1>
		<div class="ml-auto flex min-w-0 max-w-full gap-2">
			<div>
				<Button variant="solid" v-if="selectionMode && selectedPages.size" @click="promptSelectFolder()">
					{{ __("Move To Folder") }}
				</Button>
			</div>
			<div class="relative flex w-48 min-w-0 shrink" v-show="!selectionMode">
				<BuilderInput
					class="w-full"
					type="text"
					:placeholder="__('Filter by title or route')"
					v-model="searchFilter"
					@input="
						(value: string) => {
							searchFilter = value;
						}
					">
					<template #prefix>
						<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
					</template>
				</BuilderInput>
			</div>
			<div v-show="!selectionMode && displayType !== 'tree'">
				<DashboardFilter />
			</div>
			<div v-if="displayType === 'tree' && !selectionMode">
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
			<div class="max-sm:hidden" v-show="displayType !== 'tree' && !selectionMode">
				<Dropdown :options="sortOptions" align="end">
					<Button icon-left="lucide-arrow-up-down" :label="__('Sort')" />
					<template #item-suffix="{ item }">
						<span v-if="item.selected" class="lucide-check size-4 text-ink-gray-7" aria-hidden="true" />
					</template>
				</Dropdown>
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
import DashboardFilter from "@/components/DashboardFilter.vue";
import { useDashboardState } from "@/composables/useDashboardState";
import useBuilderStore from "@/stores/builderStore";
import { promptSelectFolder } from "@/utils/dialogs";
import { Button, Dropdown } from "frappe-ui";
import { computed } from "vue";
import ListTreeIcon from "~icons/lucide/list-tree";

const builderStore = useBuilderStore();
const {
	searchFilter,
	selectionMode,
	selectedPages,
	treeExpanded,
	displayType,
	orderBy,
	expandTreeFn,
	collapseTreeFn,
} = useDashboardState();

const sortOrders: { label: string; value: typeof orderBy.value }[] = [
	{ label: __("Last Created"), value: "creation" },
	{ label: __("Last Modified"), value: "modified" },
	{ label: __("Alphabetically (A-Z)"), value: "alphabetically_a_z" },
	{ label: __("Alphabetically (Z-A)"), value: "alphabetically_z_a" },
];

const sortOptions = computed(() =>
	sortOrders.map(({ label, value }) => ({
		label,
		selected: orderBy.value === value,
		onClick: () => (orderBy.value = value),
	})),
);
</script>
