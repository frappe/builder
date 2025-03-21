<template>
	<router-link :to="{ name: 'builder', params: { pageId: page.page_name } }" class="h-fit w-full">
		<div
			class="group relative flex w-full justify-between overflow-hidden rounded-2xl border-b-[1px] border-outline-gray-1 p-3 hover:cursor-pointer hover:bg-surface-gray-1"
			:class="{
				'bg-surface-gray-2': selected,
			}">
			<div class="flex w-[90%] gap-3">
				<img
					width="140"
					height="82"
					:src="page.preview"
					onerror="this.src='/assets/builder/images/fallback.png'"
					class="block w-36 flex-shrink-0 overflow-hidden rounded-lg bg-surface-gray-1 object-cover shadow-md" />
				<div class="flex flex-1 items-start justify-between overflow-hidden">
					<span class="flex h-full w-full flex-col justify-between text-base">
						<div>
							<div class="flex items-center gap-1">
								<p
									class="max-w-[90%] truncate font-medium text-ink-gray-9"
									:title="page.page_title || page.page_name">
									{{ page.page_title || page.page_name }}
								</p>
							</div>
							<div class="mt-2 flex items-center gap-2 text-ink-gray-6">
								<div v-show="page.published">
									<AuthenticatedUserIcon
										title="Limited access"
										class="size-4 text-ink-amber-3"
										v-if="page.authenticated_access" />
									<GlobeIcon class="size-4" title="Publicly accessible" v-else />
								</div>
								<p class="max-w-[90%] truncate text-sm">
									{{ page.route }}
								</p>
							</div>
						</div>
						<div class="flex items-baseline gap-2 text-ink-gray-6">
							<UseTimeAgo v-slot="{ timeAgo }" :time="page.modified">
								<p class="mt-1 block text-sm">Last updated {{ timeAgo }} by {{ page.modified_by }}</p>
							</UseTimeAgo>
						</div>
					</span>
				</div>
			</div>
			<div class="flex gap-2">
				<Badge theme="green" v-if="page.published" class="dark:bg-green-900 dark:text-green-400">
					Published
				</Badge>
				<Avatar
					:shape="'circle'"
					:label="page.owner"
					class="[&>div]:bg-surface-gray-2 [&>div]:text-ink-gray-4 [&>div]:group-hover:bg-surface-gray-4 [&>div]:group-hover:text-ink-gray-6"
					size="sm"
					:title="`Created by ${page.owner}`" />
				<Dropdown
					:options="[
						{ label: 'Duplicate', onClick: () => pageStore.duplicatePage(page), icon: 'copy' },
						{ label: 'View in Desk', onClick: () => openInDesk(page), icon: 'arrow-up-right' },
						{ label: 'Delete', onClick: () => pageStore.deletePage(page), icon: 'trash' },
					]"
					size="sm"
					placement="right">
					<template v-slot="{ open }">
						<FeatherIcon
							name="more-horizontal"
							class="h-4 w-4 font-bold text-ink-gray-6"
							@click="open"></FeatherIcon>
					</template>
				</Dropdown>
			</div>
		</div>
	</router-link>
</template>
<script setup lang="ts">
import AuthenticatedUserIcon from "@/components/Icons/AuthenticatedUser.vue";
import GlobeIcon from "@/components/Icons/Globe.vue";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { openInDesk } from "@/utils/helpers";
import { UseTimeAgo } from "@vueuse/components";
import { Avatar, Badge, Dropdown } from "frappe-ui";

const pageStore = usePageStore();

defineProps<{
	page: BuilderPage;
	selected: boolean;
}>();
</script>
