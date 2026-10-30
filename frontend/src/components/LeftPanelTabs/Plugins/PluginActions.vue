<template>
	<div class="flex w-full min-w-0 items-center gap-2">
		<Button
			v-if="canOpen"
			variant="solid"
			size="sm"
			icon-left="lucide-panel-right"
			label="Open"
			@click="emit('open')" />

		<span v-if="canManage" class="ml-auto inline-flex shrink-0">
			<Dropdown :options="moreActions" align="end">
				<template #trigger>
					<Button
						variant="ghost"
						size="sm"
						icon="lucide-more-horizontal"
						:disabled="working"
						aria-label="More plugin actions" />
				</template>
			</Dropdown>
		</span>
	</div>
</template>

<script setup lang="ts">
import { Button, Dropdown, type DropdownOptions } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{
	canOpen: boolean;
	canManage: boolean;
	enabled: boolean;
	working: boolean;
}>();

const emit = defineEmits<{
	open: [];
	setEnabled: [enabled: boolean];
	uninstall: [];
}>();

const moreActions = computed<DropdownOptions>(() => [
	{
		label: props.enabled ? "Disable" : "Enable",
		icon: props.enabled ? "lucide-power-off" : "lucide-power",
		onClick: () => emit("setEnabled", !props.enabled),
	},
	{
		label: "Uninstall",
		icon: "lucide-trash-2",
		theme: "red",
		onClick: () => emit("uninstall"),
	},
]);
</script>
