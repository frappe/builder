<template>
	<div class="flex h-full flex-col items-center justify-center gap-4 py-24 text-center">
		<div class="flex h-12 w-12 items-center justify-center rounded-full bg-surface-gray-2">
			<span class="lucide-bar-chart-2 size-6 text-ink-gray-5" aria-hidden="true" />
		</div>
		<div class="flex flex-col gap-1">
			<h3 class="text-md-medium text-ink-gray-9">{{ __("View tracking is off") }}</h3>
			<p class="max-w-sm text-p-sm text-ink-gray-6">
				{{
					__(
						"Turn on view tracking to start collecting page views, clicks and click-through rates for your published pages.",
					)
				}}
			</p>
		</div>
		<Button variant="solid" :loading="websiteSettings.setValue?.loading" @click="enableTracking">
			{{ __("Enable View Tracking") }}
		</Button>
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { websiteSettings } from "@/data/websiteSettings";
import { Button } from "frappe-ui";

const enableTracking = () => {
	websiteSettings.setValue.submit({ enable_view_tracking: 1 });
};
</script>
