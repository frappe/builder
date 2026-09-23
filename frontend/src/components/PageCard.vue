<template>
	<router-link :to="{ name: 'builder', params: { pageId: page.page_name } }">
		<div
			class="group relative flex w-full cursor-pointer flex-col gap-2 rounded-8 p-3 hover:bg-surface-elevation-1"
			:class="{
				'!bg-surface-gray-2': selected,
			}">
			<img
				width="250"
				height="140"
				:src="page.meta_image || page.preview"
				onerror="this.src='/assets/builder/images/fallback.png'"
				alt=""
				class="block aspect-video w-full overflow-hidden rounded-5 object-cover shadow dark:border dark:border-outline-gray-1" />
			<div class="flex items-center gap-1">
				<div class="min-w-0 flex-1">
					<p class="text-base-medium truncate text-ink-gray-7 group-hover:text-ink-gray-9">
						{{ page.page_title || page.page_name }}
					</p>
					<UseTimeAgo v-slot="{ timeAgo }" :time="timestamp">
						<PageStatusLine
							:page="page"
							class="mt-1"
							:time="sortedByCreation ? __('Created {0}', [timeAgo]) : __('Edited {0}', [timeAgo])" />
					</UseTimeAgo>
				</div>
				<div class="flex shrink-0 items-center gap-1.5">
					<Tooltip
						v-if="(page.published || page.staging) && page.authenticated_access"
						:text="__('This page has limited access')"
						:hoverDelay="500">
						<span class="lucide-shield-user size-3.5 text-ink-amber-6" />
					</Tooltip>
					<PageActionsDropdown :page="page" size="xs" align="end" v-slot="{ open }">
						<Button
							icon="lucide-more-horizontal"
							size="sm"
							variant="ghost"
							class="!text-ink-gray-5 opacity-0 hover:!text-ink-gray-9 focus-visible:opacity-100 group-hover:opacity-100"
							:class="{ '!opacity-100': selected || open }"
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
import PageStatusLine from "@/components/PageStatusLine.vue";
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
