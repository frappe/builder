<template>
	<div class="flex flex-col gap-5">
		<Switch
			size="sm"
			label="Execute Block Scripts in Editor"
			description="Tries to best emulate how blocks will look like on the live site by executing Block Scripts."
			:modelValue="Boolean(builderSettings.doc?.execute_block_scripts_in_editor)"
			@update:modelValue="
				(val: Boolean) => {
					builderStore.updateBuilderSettings('execute_block_scripts_in_editor', val);
				}
			" />
	</div>
</template>
<script setup lang="ts">
import Switch from "@/components/Controls/Switch.vue";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";

const builderStore = useBuilderStore();

</script>
