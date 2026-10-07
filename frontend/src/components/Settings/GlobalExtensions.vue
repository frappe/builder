<template>
	<div class="flex flex-col gap-5">
		<Switch
			size="sm"
			:label="__('Disable Extensions')"
			:description="
				__('Turns off all installed extensions and removes the Extensions tab.')
			"
			:modelValue="Boolean(builderSettings.doc?.disable_extensions)"
			@update:modelValue="
				(val: Boolean) => {
					builderStore.updateBuilderSettings('disable_extensions', val);
				}
			" />

		<hr class="w-full boder-outline-gray-2" />

		<BuilderInput
			type="text"
			class="[&>p]:text-p-xs"
			:disabled="builderSettings.doc?.disable_extensions"
			:label="__('Hub URL')"
			:description="__('Fetch the extensions catalog from this URL')"
			placeholder="preview.frappe.cloud"
			:modelValue="builderSettings.doc?.hub_url"
			:hideClearButton="true"
			@update:modelValue="(val: string) => builderStore.updateBuilderSettings('hub_url', val)" />
	</div>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import { Switch } from "frappe-ui";

const builderStore = useBuilderStore();
</script>
