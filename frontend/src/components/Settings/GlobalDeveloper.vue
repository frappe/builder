<template>
	<div class="flex flex-col gap-5">
		<div class="flex justify-between">
			<label class="w-fit text-p-base shrink-0 font-medium text-ink-gray-8">Execute Block Client Scripts in Editor</label>
			<Select
				class="w-[200px]"
				:modelValue="builderSettings.doc?.execute_block_scripts_in_editor"
				@update:modelValue="
					(value) => builderStore.updateBuilderSettings('execute_block_scripts_in_editor', value)
				"
				:options="[
					{ label: 'Don\'t Execute', value: 'Don\'t Execute' },
					{ label: 'Restricted', value: 'Restricted' },
					{ label: 'Unrestricted', value: 'Unrestricted' },
				]" />
		</div>
		<Switch
			size="sm"
			label="Prevent Click Emulation"
			description="Prevents click events from being emulated in the editor for blocks with Block Client Scripts."
			:modelValue="Boolean(builderSettings.doc?.block_click_handlers)"
			@update:modelValue="
				(val: Boolean) => {
					builderStore.updateBuilderSettings('block_click_handlers', val);
				}
			" />
		<div class="flex flex-col gap-2">
			<p class="text-sm font-medium text-ink-gray-9">
				Note: Block Scripts are executed in a sandboxed environment. This may have limitations and might not
				perfectly replicate live site behavior. Executing untrusted scripts could be unsafe.
			</p>
		</div>
	</div>
</template>
<script setup lang="ts">
import Switch from "@/components/Controls/Switch.vue";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import { Select } from "frappe-ui";
import InlineInput from "../Controls/InlineInput.vue";

const builderStore = useBuilderStore();
</script>
