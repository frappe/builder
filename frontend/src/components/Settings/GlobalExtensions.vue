<template>
	<div class="flex flex-col gap-5">
		<Switch
			size="sm"
			:label="__('Disable Extensions')"
			:description="__('Stops all extensions and hides the Extensions tab, only for you.')"
			v-model="extensionsDisabled" />

		<hr class="w-full boder-outline-gray-2" />

		<BuilderInput
			type="text"
			class="[&>p]:text-p-xs"
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
import { extensionsDisabled } from "@/data/extensions";
import useBuilderStore from "@/stores/builderStore";
import { Switch } from "frappe-ui";

const builderStore = useBuilderStore();
</script>
