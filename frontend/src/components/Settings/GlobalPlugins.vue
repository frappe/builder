<template>
	<PluginsPanel v-if="!pluginsDisabled" />
	<!-- as the Analytics pane when view tracking is off. The power button in the list turns plugins off -->
	<div v-else class="flex h-full flex-col items-center justify-center gap-4 py-24 text-center">
		<div class="flex h-12 w-12 items-center justify-center rounded-full bg-surface-gray-2">
			<span class="lucide-plug size-6 text-ink-gray-5" aria-hidden="true" />
		</div>
		<div class="flex flex-col gap-1">
			<h3 class="text-md-medium text-ink-gray-9">{{ __("Plugins are off") }}</h3>
			<p class="max-w-sm text-p-sm text-ink-gray-6">
				{{ __("Turn plugins on to load them in your editor again.") }}
			</p>
		</div>
		<Button variant="solid" @click="setPluginsDisabled(false)">{{ __("Turn On Plugins") }}</Button>
	</div>
</template>
<script setup lang="ts">
import PluginsPanel from "@/components/Settings/Plugins/PluginsPanel.vue";
import { pluginsDisabled, setPluginsDisabled } from "@/data/plugins";
import { __ } from "@/translation";
import { Button } from "frappe-ui";
</script>
