<template>
	<div class="flex flex-col gap-5">
		<div class="flex justify-between">
			<label class="text-p-base-medium w-fit shrink-0 text-ink-gray-8">Client Script Emulation</label>
			<Select
				class="!w-[200px]"
				:modelValue="builderSettings.doc?.execute_block_scripts_in_editor"
				@update:modelValue="
					(value) => builderStore.updateBuilderSettings('execute_block_scripts_in_editor', value)
				"
				:options="[
					{ label: 'Enable', value: 'Enable' },
					{ label: 'Disable', value: 'Disable' },
				]" />
		</div>
		<div class="flex flex-col gap-2">
			<p class="text-p-sm text-ink-gray-7">
				Client scripts run inside the isolated canvas document. Only enable emulation for scripts you trust.
			</p>
		</div>
	</div>
</template>
<script setup lang="ts">
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import { Select } from "frappe-ui";

const builderStore = useBuilderStore();
</script>
