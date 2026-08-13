<template>
	<div v-if="loading || rows?.length">
		<h3 class="text-lg-medium mb-4 text-ink-gray-7">{{ __("Top Referrers") }}</h3>
		<div v-if="loading" class="flex h-[200px] items-center justify-center py-8 text-sm text-ink-gray-4">
			{{ __("Loading...") }}
		</div>
		<ListView
			v-else
			class="!w-auto"
			:columns="[
				{
					label: __('Domain'),
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
				{ label: __('Count'), key: 'count', align: 'right' },
			]"
			:options="{ selectable: false, emptyState: {} }"
			:rows="rows"
			row-key="domain" />
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { ListView } from "frappe-ui";
import { h } from "vue";

defineProps<{ rows?: Array<{ domain: string; count: number | string }>; loading?: boolean }>();
</script>
