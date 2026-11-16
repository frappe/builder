<template>
	<div class="flex flex-col items-start gap-3">
		<p class="text-p-sm text-ink-gray-6">
			{{ __("Custom domains for this site are added and verified on your dashboard.") }}
		</p>
		<Button
			variant="solid"
			icon-right="lucide-arrow-up-right"
			:label="__('Open Dashboard')"
			:href="fp.dashboard_url" />
	</div>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import { fp } from "@/utils/frappePage";
import { Button } from "frappe-ui";
</script>
