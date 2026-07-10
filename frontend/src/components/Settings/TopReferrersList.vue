<template>
	<div>
		<h3 class="text-lg-medium mb-4 text-ink-gray-7">Top Referrers</h3>
		<div v-if="loading" class="flex h-[200px] items-center justify-center py-8 text-sm text-ink-gray-4">
			Loading...
		</div>
		<ListView
			v-else-if="rows?.length"
			class="!w-auto"
			:columns="[
				{
					label: 'Domain',
					key: 'domain',
					width: '60%',
					prefix: ({ row }: { row: any }) => {
						return h('img', {
							src: `https://${row.domain}/favicon.ico`,
							alt: row.domain,
							class: 'inline-block mr-2 w-5 h-5 align-middle rounded',
							onError: (e: Event) => {
								const img = e.target as HTMLImageElement | null;
								if (img) {
									img.src = '/assets/builder/images/fallback-favicon.ico';
								}
							},
						});
					},
				},
				{ label: 'Count', key: 'count', align: 'right' },
			]"
			:options="{ selectable: false, emptyState: {} }"
			:rows="rows"
			row-key="domain" />
		<AnalyticsEmptyState v-else title="No referrers yet" />
	</div>
</template>

<script setup lang="ts">
import AnalyticsEmptyState from "@/components/Settings/AnalyticsEmptyState.vue";
import { ListView } from "frappe-ui";
import { h } from "vue";

defineProps<{ rows?: Array<{ domain: string; count: number | string }>; loading?: boolean }>();
</script>
