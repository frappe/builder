<template>
	<router-link :to="{ name: 'builder', params: { pageId: page.page_name } }">
		<div
			class="group relative flex w-full cursor-pointer flex-col gap-2 rounded-2xl p-3 hover:bg-surface-elevation-1"
			:class="{
				'!bg-surface-gray-2': selected,
			}">
			<div class="relative">
				<img
					width="250"
					height="140"
					:src="page.meta_image || page.preview"
					onerror="this.src='/assets/builder/images/fallback.png'"
					alt=""
					class="block aspect-video w-full overflow-hidden rounded-md object-cover shadow dark:border dark:border-outline-gray-1" />
				<span class="absolute left-2 top-2 flex">
					<PageStatusBadge :page="page" />
				</span>
			</div>
			<div class="flex items-center justify-between border-outline-gray-2">
				<span class="inline-block min-w-0 max-w-[160px]">
					<div class="flex items-center gap-1">
						<p class="text-base-medium truncate text-ink-gray-7 group-hover:text-ink-gray-9">
							{{ page.page_title || page.page_name }}
						</p>
					</div>
					<UseTimeAgo v-slot="{ timeAgo }" :time="timestamp">
						<p class="mt-1 block truncate text-sm text-ink-gray-5 group-hover:text-ink-gray-6">
							{{ sortedByCreation ? __("Created {0}", [timeAgo]) : __("Edited {0}", [timeAgo]) }}
						</p>
					</UseTimeAgo>
				</span>
				<div class="flex shrink-0 items-center gap-1.5">
					<Tooltip
						v-if="(page.published || page.staging) && page.authenticated_access"
						:text="__('This page has limited access')"
						:hoverDelay="0.5">
						<span class="lucide-shield-user size-3.5 text-ink-amber-6" />
					</Tooltip>
					<PageActionsDropdown :page="page" size="xs" placement="right">
						<Button
							icon="lucide-more-horizontal"
							size="sm"
							variant="ghost"
							class="bg-surface-elevation-1 !text-ink-gray-5 hover:!text-ink-gray-9"
							@click.stop></Button>
					</PageActionsDropdown>
				</div>
			</div>
		</div>
	</router-link>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import PageActionsDropdown from "@/components/PageActionsDropdown.vue";
import { useDashboardState } from "@/composables/useDashboardState";
import PageStatusBadge from "@/components/PageStatusBadge.vue";
import { BuilderPage } from "@/types/doctypes";
import { UseTimeAgo } from "@vueuse/components";
import { Tooltip } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{
	page: BuilderPage;
	selected: boolean;
}>();

const { orderBy } = useDashboardState();
const sortedByCreation = computed(() => orderBy.value === "creation");
const timestamp = computed(() => (sortedByCreation.value ? props.page.creation : props.page.modified));
</script>
