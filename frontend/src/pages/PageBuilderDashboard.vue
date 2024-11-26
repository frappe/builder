<template>
	<div class="flex h-screen flex-col">
		<!-- toolbar -->
		<div
			class="toolbar sticky top-0 z-10 flex h-12 items-center justify-between border-b-[1px] border-outline-gray-1 bg-surface-white p-2 px-3 py-1"
			ref="toolbar">
			<div>
				<Dialog
					v-model="showSettingsDialog"
					style="z-index: 40"
					class="[&>div>div[id^=headlessui-dialog-panel]]:my-3"
					:disableOutsideClickToClose="true"
					:options="{
						title: 'Settings',
						size: '5xl',
					}">
					<template #body>
						<Settings @close="showSettingsDialog = false" :onlyGlobal="true"></Settings>
					</template>
				</Dialog>
				<div class="flex items-center">
					<Dropdown
						:options="[
							{
								group: 'Builder',
								hideLabel: true,
								items: [
									{
										label: 'New Page',
										onClick: () => $router.push({ name: 'builder', params: { pageId: 'new' } }),
										icon: 'plus',
									},
								],
							},
							{
								group: 'Options',
								hideLabel: true,
								items: [
									{
										label: `Apps`,
										component: AppsMenu,
										icon: 'grid',
									},
									{
										label: `Toggle Theme`,
										onClick: () => toggleDark(),
										icon: isDark ? 'sun' : 'moon',
									},
									{
										label: 'Settings',
										onClick: () => (showSettingsDialog = true),
										icon: 'settings',
									},
								],
							},
						]"
						size="sm"
						class="flex-1 [&>div>div>div]:w-full"
						placement="right">
						<template v-slot="{ open }">
							<div class="flex cursor-pointer items-center gap-2">
								<img src="/builder_logo.png" alt="logo" class="h-7" />
								<h1 class="text-md mt-[2px] font-semibold leading-5 text-gray-800 dark:text-gray-200">
									Builder
								</h1>
								<FeatherIcon
									:name="open ? 'chevron-up' : 'chevron-down'"
									class="h-4 w-4 !text-gray-700 dark:!text-gray-200"></FeatherIcon>
							</div>
						</template>
					</Dropdown>
				</div>
			</div>
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
		<div class="flex w-full flex-1 overflow-hidden">
			<!-- Sidebar -->
			<DashboardSidebar @openSettings="showSettingsDialog = true"></DashboardSidebar>
			<!-- Main Content -->
			<div class="flex-1 overflow-auto">
				<section class="m-auto mb-32 flex h-fit w-3/4 max-w-6xl flex-col pt-10">
					<!-- list head -->
					<div class="mb-8 flex items-center justify-between px-3">
						<h1 class="text-xl font-semibold text-ink-gray-9">All Pages</h1>
						<div class="flex gap-2">
							<div class="relative flex">
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
							<div class="max-md:hidden">
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
							<div class="max-sm:hidden">
								<BuilderInput
									type="select"
									class="w-32"
									v-model="orderBy"
									:options="[
										{ label: 'Sort', value: '', disabled: true },
										{ label: 'Last Created', value: 'creation' },
										{ label: 'Last Modified', value: 'modified' },
										{ label: 'Alphabetically (A-Z)', value: 'alphabetically_a_z' },
										{ label: 'Alphabetically (Z-A)', value: 'alphabetically_z_a' },
									]" />
							</div>
							<div class="max-md:hidden">
								<OptionToggle
									class="[&>div]:min-w-0"
									:options="[
										{ label: 'Grid', value: 'grid', icon: 'grid', hideLabel: true },
										{ label: 'List', value: 'list', icon: 'list', hideLabel: true },
									]"
									v-model="displayType"></OptionToggle>
							</div>
						</div>
					</div>
					<!-- pages -->
					<div>
						<div v-if="!webPages.data?.length && !searchFilter && !typeFilter" class="col-span-full">
							<p class="mt-4 text-base text-gray-500">
								You don't have any pages yet. Click on the "+ New" button to create a new page.
							</p>
						</div>
						<div v-else-if="!webPages.data?.length" class="col-span-full">
							<p class="mt-4 text-base text-gray-500">No matching pages found.</p>
						</div>
						<!-- grid -->
						<div class="grid-col grid gap-3 auto-fill-[220px]" v-if="displayType === 'grid'">
							<PageCard v-for="page in webPages.data" :key="page.page_name" :page="page"></PageCard>
						</div>
						<!-- list -->
						<div v-if="displayType === 'list'">
							<PageListItem v-for="page in webPages.data" :key="page.page_name" :page="page"></PageListItem>
						</div>
					</div>
					<BuilderButton
						class="m-auto mt-12 w-fit text-sm dark:bg-zinc-900 dark:text-zinc-300"
						@click="loadMore"
						v-show="webPages.hasNextPage"
						variant="subtle"
						size="sm">
						Load More
					</BuilderButton>
				</section>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import AppsMenu from "@/components/AppsMenu.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import DashboardSidebar from "@/components/DashboardSidebar.vue";
import PageCard from "@/components/PageCard.vue";
import PageListItem from "@/components/PageListItem.vue";
import Settings from "@/components/Settings.vue";
import { webPages } from "@/data/webPage";
import useStore from "@/store";
import { posthog } from "@/telemetry";
import { useDark, useStorage, useToggle, watchDebounced } from "@vueuse/core";
import { Dropdown } from "frappe-ui";
import { onActivated, Ref, ref } from "vue";

const isDark = useDark({
	attribute: "data-theme",
});
const toggleDark = useToggle(isDark);
const store = useStore();
const displayType = useStorage("displayType", "grid") as Ref<"grid" | "list">;

const searchFilter = ref("");
const typeFilter = ref("");
const orderBy = useStorage("orderBy", "creation") as Ref<
	"creation" | "modified" | "alphabetically_a_z" | "alphabetically_z_a"
>;

const showDialog = ref(false);

const orderMap = {
	creation: "creation desc",
	modified: "modified desc",
	alphabetically_a_z: "page_title asc",
	alphabetically_z_a: "page_title desc",
};

onActivated(() => {
	posthog.capture("builder_dashboard_page_visited");
});

watchDebounced(
	[searchFilter, typeFilter, orderBy],
	() => {
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
		webPages.update({
			filters,
			orFilters,
			orderBy: orderMap[orderBy.value],
		});
		webPages.fetch();
	},
	{ debounce: 300, immediate: true },
);

const loadMore = () => {
	webPages.next();
};

const showSettingsDialog = ref(false);
</script>
