<template>
	<div class="flex w-full min-w-0 items-center gap-2">
		<Button
			v-if="canOpen"
			variant="solid"
			size="sm"
			icon-left="lucide-panel-right"
			label="Open"
			@click="emit('open')" />

		<span v-if="moreActions.length" class="ml-auto inline-flex shrink-0">
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
	/** An app's plugin goes with the app, so it has no Uninstall. */
	canUninstall: boolean;
	enabled: boolean;
	working: boolean;
	/** Unset when the plugin has no left bar tab. */
	tabHidden?: boolean;
}>();

const emit = defineEmits<{
	open: [];
	setEnabled: [enabled: boolean];
	setTabHidden: [hidden: boolean];
	uninstall: [];
}>();

// hiding a tab is this user's own choice, so it shows for everyone; the rest changes the site
const tabActions = computed<DropdownOptions>(() =>
	props.tabHidden === undefined
		? []
		: [
				{
					label: props.tabHidden ? "Show in left bar" : "Hide from left bar",
					icon: props.tabHidden ? "lucide-eye" : "lucide-eye-off",
					onClick: () => emit("setTabHidden", !props.tabHidden),
				},
			],
);

const managerActions = computed<DropdownOptions>(() => {
	if (!props.canManage) return [];
	const actions: DropdownOptions = [
		{
			label: props.enabled ? "Disable" : "Enable",
			icon: props.enabled ? "lucide-power-off" : "lucide-power",
			onClick: () => emit("setEnabled", !props.enabled),
		},
	];
	if (props.canUninstall) {
		actions.push({
			label: "Uninstall",
			icon: "lucide-trash-2",
			theme: "red",
			onClick: () => emit("uninstall"),
		});
	}
	return actions;
});

const moreActions = computed<DropdownOptions>(() => [...tabActions.value, ...managerActions.value]);
</script>
