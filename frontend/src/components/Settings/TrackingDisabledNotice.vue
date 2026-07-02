<template>
	<div class="flex h-full flex-col items-center justify-center gap-4 py-24 text-center">
		<div class="flex h-12 w-12 items-center justify-center rounded-full bg-surface-gray-2">
			<FeatherIcon name="bar-chart-2" class="h-6 w-6 text-ink-gray-5" />
		</div>
		<div class="flex flex-col gap-1">
			<h3 class="text-lg-medium text-ink-gray-9">View tracking is off</h3>
			<p class="max-w-sm text-p-sm text-ink-gray-6">
				Turn on view tracking to start collecting page views, clicks and click-through rates for your
				published pages.
			</p>
		</div>
		<div class="flex items-center gap-3">
			<Button variant="solid" :loading="websiteSettings.setValue?.loading" @click="enableTracking">
				Enable View Tracking
			</Button>
			<Button v-if="selectSettingsTab" variant="ghost" @click="selectSettingsTab('global_general')">
				Open Global Settings
			</Button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { websiteSettings } from "@/data/websiteSettings";
import { Button, FeatherIcon } from "frappe-ui";
import { inject } from "vue";

const selectSettingsTab = inject<((tab: string) => void) | null>("selectSettingsTab", null);

const enableTracking = () => {
	websiteSettings.setValue.submit({ enable_view_tracking: 1 });
};
</script>
