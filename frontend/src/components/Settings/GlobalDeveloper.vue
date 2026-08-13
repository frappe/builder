<template>
	<div class="flex flex-col gap-5">
		<div class="flex justify-between">
			<label class="text-p-base-medium w-fit shrink-0 text-ink-gray-8">
				{{ __("Execute Block Client Scripts in Editor") }}
			</label>
			<Select
				class="!w-[200px]"
				:modelValue="builderSettings.doc?.execute_block_scripts_in_editor"
				@update:modelValue="
					(value) => builderStore.updateBuilderSettings('execute_block_scripts_in_editor', value)
				"
				:options="[
					{ label: __('Don\'t Execute'), value: 'Don\'t Execute' },
					{ label: __('Restricted'), value: 'Restricted' },
					{ label: __('Unrestricted'), value: 'Unrestricted' },
				]" />
		</div>
		<Switch
			size="sm"
			:label="__('Prevent Click Emulation')"
			:description="
				__('Prevents click events from being emulated in the editor for blocks with Block Client Scripts.')
			"
			:modelValue="Boolean(builderSettings.doc?.restrict_click_handlers)"
			@update:modelValue="
				(val: Boolean) => {
					builderStore.updateBuilderSettings('restrict_click_handlers', val);
				}
			" />
		<p class="text-p-sm text-ink-gray-5">
			{{
				__(
					"Note: Block Scripts are executed in a sandboxed environment. This may have limitations and might not perfectly replicate live site behavior. Executing untrusted scripts could be unsafe.",
				)
			}}
		</p>
	</div>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import { Select, Switch } from "frappe-ui";

const builderStore = useBuilderStore();
</script>
