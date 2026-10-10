<template>
	<div class="flex items-center">
		<Popover align="end" @open="pageCreators.fetch()">
			<template #trigger>
				<Button
					icon-left="lucide-list-filter"
					:label="__('Filter')"
					:class="{ 'rounded-r-none': activeFilterCount }">
					<template #suffix v-if="activeFilterCount">
						<span
							class="text-xs-medium flex size-5 items-center justify-center rounded-[5px] bg-surface-base pt-px text-ink-gray-8 shadow-sm">
							{{ activeFilterCount }}
						</span>
					</template>
				</Button>
			</template>
			<div class="grid grid-cols-[auto_12rem] items-center gap-x-3 gap-y-2 p-2">
				<span class="pl-1 text-base text-ink-gray-5">{{ __("Status") }}</span>
				<Combobox v-model="status" trigger="button" hide-search :options="statusOptions" />
				<span class="pl-1 text-base text-ink-gray-5">{{ __("Access") }}</span>
				<Combobox v-model="access" trigger="button" hide-search :options="accessOptions" />
				<span class="pl-1 text-base text-ink-gray-5">{{ __("Created by") }}</span>
				<Combobox v-model="createdBy" trigger="button" :placeholder="__('Anyone')" :options="creatorOptions">
					<template #prefix="{ selectedOption }">
						<Avatar
							v-if="selectedOption"
							size="xs"
							:image="selectedOption.image"
							:label="selectedOption.label" />
					</template>
					<template #item-prefix="{ item }">
						<Avatar size="sm" :image="item.image" :label="item.label" />
					</template>
				</Combobox>
			</div>
		</Popover>
		<Button
			v-if="activeFilterCount"
			icon="lucide-x"
			:label="__('Clear All Filters')"
			:tooltip="__('Clear All Filters')"
			class="rounded-l-none border-l border-outline-gray-2"
			@click="clearFilters" />
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { useDashboardState } from "@/composables/useDashboardState";
import { pageCreators } from "@/data/webPage";
import { sessionUser } from "@/router";
import { getUsersInfo } from "@/usersInfo";
import { Avatar, Button, Combobox, Popover, type ComboboxOptionValue } from "frappe-ui";
import { computed, type Ref } from "vue";

const { statusFilter, accessFilter, createdByFilter, activeFilterCount } = useDashboardState();

const statusOptions: { label: string; value: Exclude<typeof statusFilter.value, ""> }[] = [
	{ label: __("All"), value: "all" },
	{ label: __("Live"), value: "live" },
	{ label: __("Staging"), value: "staging" },
	{ label: __("Draft"), value: "draft" },
	{ label: __("Unpublished changes"), value: "unpublished_changes" },
];

const accessOptions: { label: string; value: typeof accessFilter.value }[] = [
	{ label: __("All"), value: "all" },
	{ label: __("Public"), value: "public" },
	{ label: __("Protected"), value: "protected" },
];

// options lead with "all", which also stands in for the legacy empty status
const optionModel = <T extends string>(filter: Ref<T | "">, options: { value: T }[]) =>
	computed<ComboboxOptionValue | null>({
		get: () => filter.value || options[0].value,
		set: (value) =>
			(filter.value = options.find((option) => option.value === value)?.value ?? options[0].value),
	});

const status = optionModel(statusFilter, statusOptions);
const access = optionModel(accessFilter, accessOptions);

const createdBy = computed<ComboboxOptionValue | null>({
	get: () => createdByFilter.value || null,
	set: (value) => (createdByFilter.value = value ? String(value) : ""),
});

const creatorOptions = computed(() => {
	const owners = (pageCreators.data || []).map((row: { owner: string }) => row.owner);
	return getUsersInfo(owners)
		.map((user) => ({ label: user.fullname, value: user.user, image: user.image }))
		.sort((a, b) => Number(b.value === sessionUser.value) - Number(a.value === sessionUser.value));
});

const clearFilters = () => {
	statusFilter.value = "all";
	accessFilter.value = "all";
	createdByFilter.value = "";
};
</script>
