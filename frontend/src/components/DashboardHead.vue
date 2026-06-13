<template>
	<div class="m-auto flex w-3/4 max-w-6xl items-center justify-between bg-surface-base px-3.5 py-5 pt-8">
		<h1 class="text-3xl-semibold text-ink-gray-9">
			{{ builderStore.activeFolder || "All Pages" }}
		</h1>
		<div class="flex gap-2">
			<div>
				<Button variant="solid" v-if="selectionMode && selectedPages.size" @click="promptSelectFolder()">
					Move To Folder
				</Button>
			</div>
			<div class="relative flex" v-show="!selectionMode">
				<BuilderInput
					class="w-48"
					type="text"
					placeholder="Filter by title or route"
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
			<div class="max-md:hidden" v-show="!selectionMode && displayType !== 'tree'">
				<Select
					v-model="typeFilter"
					:options="[
						{ label: 'Type', value: '', disabled: true },
						{ label: 'All', value: 'all' },
						{ label: 'Draft', value: 'draft' },
						{ label: 'Published', value: 'published' },
						{ label: 'Unpublished', value: 'unpublished' },
					]" />
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
					{{ treeExpanded ? "Collapse" : "Expand" }}
				</Button>
			</div>
			<div class="max-sm:hidden" v-show="displayType !== 'tree' && !selectionMode">
				<Select
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
							icon: 'lucide-grid-2x2',
							hideLabel: true,
						},
						{
							label: 'List',
							value: 'list',
							icon: 'lucide-list',
							hideLabel: true,
						},
						{
							label: 'Route Tree',
							value: 'tree',
							icon: ListTreeIcon,
							hideLabel: true,
							showTooltip: true,
						},
					]"
					v-model="displayType"></OptionToggle>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import { useDashboardState } from "@/composables/useDashboardState";
import useBuilderStore from "@/stores/builderStore";
import { promptSelectFolder } from "@/utils/dialogs";
import { Button, Select } from "frappe-ui";
import ListTreeIcon from "~icons/lucide/list-tree";

const builderStore = useBuilderStore();
const {
	searchFilter,
	selectionMode,
	selectedPages,
	treeExpanded,
	displayType,
	typeFilter,
	orderBy,
	expandTreeFn,
	collapseTreeFn,
} = useDashboardState();
</script>
