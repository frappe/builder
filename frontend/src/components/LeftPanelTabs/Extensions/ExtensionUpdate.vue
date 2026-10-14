<template>
	<!-- shows nothing until the Hub has a newer release -->
	<div v-if="update" class="flex items-center justify-between gap-2 rounded bg-surface-gray-2 px-3 py-2">
		<span class="text-p-sm text-ink-gray-7">
			{{ isUpdating ? `Updating to ${update.version}…` : `Version ${update.version} is available.` }}
		</span>
		<Button size="sm" variant="solid" label="Update" :loading="isUpdating" @click="askUpdate" />
	</div>

	<ExtensionInstallDialog
		v-if="update"
		v-model:open="isDialogOpen"
		:title="`Update ${label}?`"
		:extension="extension"
		:label="label"
		:requested="update.new_permissions"
		@install="start" />
</template>

<script setup lang="ts">
import ExtensionInstallDialog from "@/components/LeftPanelTabs/Extensions/ExtensionInstallDialog.vue";
import { getExtensionUpdate, loadExtensions, updateFromHub, type ExtensionUpdate } from "@/data/extensions";
import useBuilderStore from "@/stores/builderStore";
import type { Permission } from "frappe-builder-extension-sdk/types";
import { Button, toast } from "frappe-ui";
import { onMounted, onUnmounted, ref, shallowRef } from "vue";

const props = defineProps<{ extension: string; label: string; granted: Permission[] }>();
/** The details page reloads its README and requested permissions. */
const emit = defineEmits<{ updated: [] }>();

const builderStore = useBuilderStore();
const update = shallowRef<ExtensionUpdate | null>(null);
const isUpdating = ref(false);
const isDialogOpen = ref(false);

/** A Hub that is down only hides the offer. The installed release still runs. */
const check = async () => {
	try {
		update.value = await getExtensionUpdate(props.extension);
	} catch (error) {
		console.warn(`Could not check "${props.extension}" for an update`, error);
	}
};

/** The manager approves only the permissions that the new release adds. */
const askUpdate = () => {
	if (update.value?.new_permissions.length) isDialogOpen.value = true;
	else start([]);
};

/** The grants that the new release still asks for stay. The approved new ones join them. */
const start = async (approved: Permission[]) => {
	isDialogOpen.value = false;
	const kept = props.granted.filter((permission) => update.value!.requested_permissions.includes(permission));
	try {
		await updateFromHub(props.extension, update.value!.version, [...kept, ...approved]);
		isUpdating.value = true;
	} catch (error) {
		toast.error((error as Error).message);
	}
};

const onUpdateDone = async (event: { extension: string; error?: string | null }) => {
	if (event.extension !== props.extension || !isUpdating.value) return;
	isUpdating.value = false;
	if (event.error) toast.error(event.error);
	else toast.success(`${props.label} is up to date`);
	// a new build has a new entry URL, so the editor loads the new code
	await loadExtensions();
	await check();
	emit("updated");
};

onMounted(() => {
	check();
	builderStore.realtime.on("builder_extension_update", onUpdateDone);
});
onUnmounted(() => builderStore.realtime.off("builder_extension_update", onUpdateDone));
</script>
