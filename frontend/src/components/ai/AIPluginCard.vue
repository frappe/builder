<template>
	<div
		v-if="installation"
		class="flex items-center gap-2.5 rounded-6 border border-outline-gray-2 bg-surface-base px-2.5 py-2">
		<img
			v-if="installation.icon"
			:src="installation.icon"
			class="size-4 shrink-0 object-contain"
			alt=""
			aria-hidden="true" />
		<span v-else class="lucide-plug size-4 shrink-0 text-ink-gray-6" aria-hidden="true" />
		<div class="flex min-w-0 flex-1 flex-col">
			<span class="truncate text-sm font-medium text-ink-gray-9">{{ installation.label }}</span>
			<span v-if="installation.description" class="line-clamp-2 text-p-xs text-ink-gray-5">
				{{ installation.description }}
			</span>
		</div>
		<Button v-if="openHandler" variant="subtle" size="sm" label="Open" @click="openHandler()" />
		<Tooltip v-if="canManagePlugins" text="Remove">
			<Button
				variant="ghost"
				size="sm"
				icon="lucide-trash-2"
				aria-label="Remove"
				:loading="removing"
				@click="remove" />
		</Tooltip>
	</div>
	<p v-else-if="listChecked" class="text-p-xs italic text-ink-gray-5">This plugin was removed.</p>
</template>

<script setup lang="ts">
import { canManagePlugins, installations, reloadInstallations, uninstallPlugin } from "@/data/plugins";
import { openHandlers } from "@/plugins/context";
import { confirm } from "@/utils/helpers";
import { Button, toast, Tooltip } from "frappe-ui";
import { computed, onMounted, ref } from "vue";

/** The card reads the live installation list, so a change in the Plugins panel shows here too. */
const props = defineProps<{ plugin: string }>();

const installation = computed(() => installations.value.find((row) => row.name === props.plugin));
const openHandler = computed(() => openHandlers.get(props.plugin));
const removing = ref(false);

// a plugin that failed to load in this tab never refreshed the list, so ask once before calling it removed
const listChecked = ref(false);
onMounted(async () => {
	if (!installation.value) await reloadInstallations();
	listChecked.value = true;
});

const remove = async () => {
	const label = installation.value?.label ?? props.plugin;
	if (!(await confirm("It goes for everyone who edits this site.", `Remove ${label}?`))) return;
	removing.value = true;
	try {
		await uninstallPlugin(props.plugin);
	} catch (error) {
		toast.error((error as Error).message);
	} finally {
		removing.value = false;
	}
};
</script>
