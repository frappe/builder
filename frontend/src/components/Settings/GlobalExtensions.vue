<template>
	<div class="flex flex-col gap-5">
		<Alert theme="amber" :title="__('Extensions are experimental. They can change between releases.')" />
		<Switch
			size="sm"
			:label="__('Disable Extensions')"
			:description="
				__(
					'Stops all extensions and hides the Extensions tab, only for you. It applies from the next reload.',
				)
			"
			v-model="extensionsDisabled" />

		<hr class="w-full border-outline-gray-2" />

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
import { extensionsDisabled } from "@/data/extensions";
import { __ } from "@/translation";
import { Alert, Switch } from "frappe-ui";
</script>
