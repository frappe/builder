<template>
	<div class="flex items-center gap-2">
		<Button
			v-if="openHandler"
			variant="solid"
			size="sm"
			icon-left="lucide-panel-right"
			label="Open"
			@click="openHandler()" />
		<Tooltip
			v-if="plugin.has_draft"
			text="Only a System Manager or a Website Manager can share plugins."
			:disabled="canManagePlugins">
			<div>
				<Button
					variant="subtle"
					size="sm"
					icon-left="lucide-users"
					:label="plugin.is_shared ? 'Share update' : 'Share'"
					:disabled="!canManagePlugins || working"
					@click="isShareDialogOpen = true" />
			</div>
		</Tooltip>
		<Tooltip v-if="plugin.has_draft" :text="plugin.is_shared ? 'Discard your changes' : 'Remove'">
			<Button
				class="ml-auto"
				variant="ghost"
				size="sm"
				:icon="plugin.is_shared ? 'lucide-undo-2' : 'lucide-trash-2'"
				:aria-label="plugin.is_shared ? 'Discard your changes' : 'Remove'"
				:loading="working"
				@click="discard" />
		</Tooltip>

		<PluginShareDialog
			v-model:open="isShareDialogOpen"
			:plugin="plugin.name"
			:label="plugin.label ?? plugin.name"
			:is-update="Boolean(plugin.is_shared)"
			@share="share" />
	</div>
</template>

<script setup lang="ts">
import PluginShareDialog from "@/components/LeftPanelTabs/Plugins/PluginShareDialog.vue";
import { canManagePlugins, discardDraft, shareDraft, type Installation } from "@/data/plugins";
import { openHandlers } from "@/plugins/context";
import { confirm } from "@/utils/helpers";
import { Button, toast, Tooltip } from "frappe-ui";
import { computed, ref } from "vue";

const props = defineProps<{ plugin: Installation }>();

const openHandler = computed(() => openHandlers.get(props.plugin.name));
const isShareDialogOpen = ref(false);
const working = ref(false);

const run = async (action: () => Promise<void>) => {
	working.value = true;
	try {
		await action();
	} catch (error) {
		toast.error((error as Error).message);
	} finally {
		working.value = false;
	}
};

const share = () => {
	isShareDialogOpen.value = false;
	return run(() => shareDraft(props.plugin.name));
};

/** A shared plugin goes back to what everyone runs. One that was never shared is gone. */
const discard = () =>
	run(async () => {
		const label = props.plugin.label ?? props.plugin.name;
		const [message, title] = props.plugin.is_shared
			? ["You go back to the version everyone runs.", `Discard your changes to ${label}?`]
			: ["Bob can build it again if you ask.", `Remove ${label}?`];
		if (await confirm(message, title)) await discardDraft(props.plugin.name);
	});
</script>
