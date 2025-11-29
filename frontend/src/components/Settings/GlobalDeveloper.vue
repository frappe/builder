<template>
	<div class="flex flex-col gap-5">
		<Switch
			size="sm"
			label="Execute Block Scripts in Editor"
			description="Tries to best emulate how blocks will look like on the live site."
			:modelValue="Boolean(builderSettings.doc?.execute_block_scripts_in_editor)"
			@update:modelValue="
				(val: Boolean) => {
					builderStore.updateBuilderSettings('execute_block_scripts_in_editor', val);
				}
			" />
		<div class="flex flex-col gap-2">
			<p class="text-sm font-medium text-ink-gray-9">
				Note: Block Scripts are executed in a sandboxed environment. This may have limitations and might not perfectly replicate live site behavior. Executing
				untrusted scripts could be unsafe.
			</p>
		</div>
	</div>
</template>
<script setup lang="ts">
import Switch from "@/components/Controls/Switch.vue";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";

const builderStore = useBuilderStore();
</script>
