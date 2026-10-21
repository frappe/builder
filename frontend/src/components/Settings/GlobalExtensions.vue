<template>
	<div class="flex flex-col gap-5">
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

		<BuilderInput
			type="text"
			class="[&>p]:text-p-xs"
			:label="__('Hub URL')"
			:description="__('Fetch the extensions catalog from this URL')"
			placeholder="https://preview.frappe.cloud"
			:modelValue="builderSettings.doc?.hub_url"
			:hideClearButton="true"
			@update:modelValue="(value: string) => builderStore.updateBuilderSettings('hub_url', value)" />
	</div>
</template>
<script setup lang="ts">
import { builderSettings } from "@/data/builderSettings";
import { extensionsDisabled } from "@/data/extensions";
import useBuilderStore from "@/stores/builderStore";
import { __ } from "@/translation";
import { Switch } from "frappe-ui";

const builderStore = useBuilderStore();
</script>
