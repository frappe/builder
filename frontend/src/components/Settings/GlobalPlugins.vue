<template>
	<div class="flex flex-col gap-5">
		<Alert theme="amber" :title="__('Plugins are experimental. They can change between releases.')" />
		<Switch
			size="sm"
			:label="__('Disable Plugins')"
			:description="__('Stops all plugins, only for you. It applies from the next reload.')"
			v-model="pluginsDisabled" />

		<hr class="w-full border-outline-gray-2" />

		<PluginsPanel v-if="!pluginsDisabled" />

		<p class="text-p-xs text-ink-gray-5">
			{{
				__(
					"The catalog comes from the Builder Hub. To use another Hub, set builder_hub_url in the site config.",
				)
			}}
		</p>
	</div>
</template>
<script setup lang="ts">
import PluginsPanel from "@/components/Settings/Plugins/PluginsPanel.vue";
import { pluginsDisabled } from "@/data/plugins";
import { __ } from "@/translation";
import { Alert, Switch } from "frappe-ui";
</script>
