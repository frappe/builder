<template>
	<router-link :to="{ name: 'builder', params: { pageId: page.page_name } }" class="group block h-fit w-full">
		<div
			class="group relative flex w-full justify-between overflow-hidden rounded-2xl p-3 hover:cursor-pointer hover:bg-surface-gray-1"
			:class="{
				'bg-surface-gray-2': selected,
			}">
			<div class="flex w-[85%] gap-3">
				<img
					width="140"
					height="82"
					:src="page.meta_image || page.preview"
					alt=""
					onerror="this.src='/assets/builder/images/fallback.png'"
					class="block aspect-video w-36 flex-shrink-0 overflow-hidden rounded-lg bg-surface-gray-1 object-cover shadow-md" />
				<div class="flex flex-1 items-start justify-between overflow-hidden">
					<span class="flex h-full w-full flex-col justify-between text-base">
						<div>
							<div class="flex items-center gap-1">
								<p class="truncate font-medium text-ink-gray-9" :title="page.page_title || page.page_name">
									{{ page.page_title || page.page_name }}
								</p>
							</div>
							<div class="mt-2 flex items-center gap-2 text-ink-gray-6">
								<span
									:title="__('Limited access')"
									class="lucide-shield-user size-4 shrink-0 text-ink-amber-6"
									v-if="(page.published || page.staging) && page.authenticated_access" />
								<p class="min-w-0 truncate text-sm" :title="page.route">
									{{ page.route }}
								</p>
							</div>
						</div>
						<div class="flex items-baseline gap-2 text-ink-gray-6">
							<UseTimeAgo v-slot="{ timeAgo }" :time="timestamp">
								<p class="mt-1 block text-sm">
									{{
										sortedByCreation
											? __("Created {0} by {1}", [timeAgo, owner.fullname])
											: __("Last updated {0} by {1}", [timeAgo, modifiedBy.fullname])
									}}
								</p>
							</UseTimeAgo>
						</div>
					</span>
				</div>
			</div>
			<div class="flex gap-2">
				<PageStatusBadge :page="page" />
				<Avatar
					:shape="'circle'"
					:image="owner.image"
					:label="owner.fullname"
					class="[&>div]:bg-surface-gray-2 [&>div]:text-ink-gray-4 [&>div]:group-hover:bg-surface-gray-4 [&>div]:group-hover:text-ink-gray-6"
					size="sm"
					:title="__('Created by {0}', [owner.fullname])" />
				<PageActionsDropdown :page="page" size="sm" placement="right">
					<span
						class="lucide-more-horizontal h-4 w-4 font-bold text-ink-gray-6"
						aria-hidden="true"
						@click.stop />
				</PageActionsDropdown>
			</div>
		</div>
		<div class="mx-4 border-b border-outline-gray-1 group-last:hidden"></div>
	</router-link>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import PageActionsDropdown from "@/components/PageActionsDropdown.vue";
import { useDashboardState } from "@/composables/useDashboardState";
import PageStatusBadge from "@/components/PageStatusBadge.vue";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/doctypes";
import { getUserInfo } from "@/usersInfo";
import { UseTimeAgo } from "@vueuse/components";
import { Avatar } from "frappe-ui";
import { computed } from "vue";

const pageStore = usePageStore();

const props = defineProps<{
	page: BuilderPage;
	selected: boolean;
}>();

const modifiedBy = getUserInfo(props.page.modified_by);
const owner = getUserInfo(props.page.owner);
const { orderBy } = useDashboardState();
const sortedByCreation = computed(() => orderBy.value === "creation");
const timestamp = computed(() => (sortedByCreation.value ? props.page.creation : props.page.modified));
</script>
