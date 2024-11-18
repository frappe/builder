<template>
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
				class="bg-surface-gray-7 !text-text-icons-white hover:bg-surface-gray-6">
				New
			</BuilderButton>
		</router-link>
	</div>
	<!-- page list wrapper -->
	<section class="m-auto mb-32 flex w-3/4 max-w-6xl flex-col pt-10">
		<!-- list head -->
		<div class="mb-8 flex items-center justify-between px-3">
			<h1 class="text-xl font-semibold text-text-icons-gray-9">All Pages</h1>
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
							<FeatherIcon name="search" class="size-4 text-text-icons-gray-5"></FeatherIcon>
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
				<router-link
					v-for="page in webPages.data"
					:key="page.page_name"
					@click="
						() => {
							posthog.capture('builder_page_opened', { page_name: page.page_name });
						}
					"
					:to="{ name: 'builder', params: { pageId: page.page_name } }">
					<div
						class="group relative flex w-full cursor-pointer flex-col gap-2 rounded-2xl bg-surface-white p-3 hover:bg-surface-gray-2">
						<img
							width="250"
							height="140"
							:src="page.preview"
							onerror="this.src='/assets/builder/images/fallback.png'"
							class="w-full overflow-hidden rounded-md object-cover shadow dark:border dark:border-outline-gray-1" />
						<div class="flex items-center justify-between border-outline-gray-2">
							<span class="inline-block max-w-[160px]">
								<div class="flex items-center gap-1">
									<p
										class="truncate text-base font-medium text-text-icons-gray-7 group-hover:text-text-icons-gray-9">
										{{ page.page_title || page.page_name }}
									</p>
								</div>
								<UseTimeAgo v-slot="{ timeAgo }" :time="page.modified">
									<p class="mt-1 block text-sm text-text-icons-gray-5 group-hover:text-text-icons-gray-6">
										Edited {{ timeAgo }}
									</p>
								</UseTimeAgo>
							</span>
							<Dropdown
								:options="[
									{
										group: 'Actions',
										hideLabel: true,
										items: [
											{ label: 'Duplicate', onClick: () => store.duplicatePage(page), icon: 'copy' },
											{
												label: 'View in Desk',
												onClick: () => store.openInDesk(page),
												icon: 'arrow-up-right',
											},
										],
									},
									{
										group: 'Delete',
										hideLabel: true,
										items: [{ label: 'Delete', onClick: () => store.deletePage(page), icon: 'trash' }],
									},
								]"
								size="xs"
								placement="right">
								<template v-slot="{ open }">
									<BuilderButton
										icon="more-horizontal"
										size="sm"
										variant="subtle"
										class="bg-surface-white !text-text-icons-gray-5 hover:!text-text-icons-gray-9"
										@click="open"></BuilderButton>
								</template>
							</Dropdown>
						</div>
					</div>
				</router-link>
			</div>
			<!-- list -->
			<div v-if="displayType === 'list'">
				<router-link
					v-for="page in webPages.data"
					:key="page.page_name"
					:to="{ name: 'builder', params: { pageId: page.page_name } }"
					@click="
						() => {
							posthog.capture('builder_page_opened', { page_name: page.page_name });
						}
					"
					class="col-span-full h-fit w-full flex-grow">
					<div
						class="group relative flex w-full gap-3 overflow-hidden border-b-[1px] border-outline-gray-1 p-3 hover:cursor-pointer hover:rounded-2xl hover:bg-surface-gray-1">
						<img
							width="140"
							height="82"
							:src="page.preview"
							onerror="this.src='/assets/builder/images/fallback.png'"
							class="block w-36 overflow-hidden rounded-lg bg-surface-gray-1 object-cover shadow-md" />
						<div class="flex flex-1 items-start justify-between">
							<span class="flex h-full flex-col justify-between text-base text-gray-700 dark:text-zinc-200">
								<div>
									<div class="flex items-center gap-1">
										<p class="truncate font-medium text-text-icons-gray-9">
											{{ page.page_title || page.page_name }}
										</p>
									</div>
									<div class="mt-2 flex items-center gap-2 text-text-icons-gray-6">
										<div v-show="page.published">
											<AuthenticatedUserIcon
												title="Limited access"
												class="size-4 text-text-icons-amber-3"
												v-if="page.authenticated_access" />
											<GlobeIcon class="size-4" title="Publicly accessible" v-else />
										</div>
										<p class="text-sm">
											{{ page.route }}
										</p>
									</div>
								</div>
								<div class="flex items-baseline gap-2 text-text-icons-gray-6">
									<UseTimeAgo v-slot="{ timeAgo }" :time="page.modified">
										<p class="mt-1 block text-sm">Last updated {{ timeAgo }} by {{ page.modified_by }}</p>
									</UseTimeAgo>
								</div>
							</span>
							<div class="flex items-center gap-2">
								<Badge theme="green" v-if="page.published" class="dark:bg-green-900 dark:text-green-400">
									Published
								</Badge>
								<Avatar
									:shape="'circle'"
									:image="null"
									:label="page.owner"
									class="[&>div]:bg-surface-gray-2 [&>div]:text-text-icons-gray-4 [&>div]:group-hover:bg-surface-gray-4 [&>div]:group-hover:text-text-icons-gray-6"
									size="sm"
									:title="`Created by ${page.owner}`" />
								<Dropdown
									:options="[
										{ label: 'Duplicate', onClick: () => store.duplicatePage(page), icon: 'copy' },
										{ label: 'View in Desk', onClick: () => store.openInDesk(page), icon: 'arrow-up-right' },
										{ label: 'Delete', onClick: () => store.deletePage(page), icon: 'trash' },
									]"
									size="sm"
									placement="right">
									<template v-slot="{ open }">
										<FeatherIcon
											name="more-horizontal"
											class="h-4 w-4 font-bold text-text-icons-gray-6"
											@click="open"></FeatherIcon>
									</template>
								</Dropdown>
							</div>
						</div>
					</div>
				</router-link>
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
</template>
<script setup lang="ts">
import AppsMenu from "@/components/AppsMenu.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import AuthenticatedUserIcon from "@/components/Icons/AuthenticatedUser.vue";
import GlobeIcon from "@/components/Icons/Globe.vue";
import Settings from "@/components/Settings.vue";
import { webPages } from "@/data/webPage";
import useStore from "@/store";
import { posthog } from "@/telemetry";
import { UseTimeAgo } from "@vueuse/components";
import { useDark, useStorage, useToggle, watchDebounced } from "@vueuse/core";
import { Avatar, Badge, Dropdown } from "frappe-ui";
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
