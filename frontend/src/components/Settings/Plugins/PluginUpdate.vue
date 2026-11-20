<template>
	<!-- shows nothing until the Hub has a newer release -->
	<div v-if="update" class="flex items-center justify-between gap-2 rounded-6 bg-surface-gray-2 px-3 py-2">
		<span class="text-p-sm text-ink-gray-7">
			{{ isUpdating ? `Updating to ${update.version}…` : `Version ${update.version} is available.` }}
		</span>
		<Button size="sm" variant="solid" label="Update" :loading="isUpdating" @click="start" />
	</div>
</template>

<script setup lang="ts">
import { getPluginUpdate, updateFromHub, updatingPlugins, type PluginUpdate } from "@/data/plugins";
import { Button, toast } from "frappe-ui";
import { computed, onMounted, shallowRef, watch } from "vue";

const props = defineProps<{ plugin: string }>();
/** The details page reloads its README. */
const emit = defineEmits<{ updated: [] }>();

const update = shallowRef<PluginUpdate | null>(null);
/** Shared, so a return to this page while the job runs still shows it. */
const isUpdating = computed(() => updatingPlugins.has(props.plugin));

/** A Hub that is down only hides the offer. The installed release still runs. */
const check = async () => {
	try {
		update.value = await getPluginUpdate(props.plugin);
	} catch (error) {
		console.warn(`Could not check "${props.plugin}" for an update`, error);
	}
};

const start = async () => {
	try {
		await updateFromHub(props.plugin, update.value!.version);
	} catch (error) {
		toast.error((error as Error).message);
	}
};

// the job's listener shows how it ended. This page only reads the new state
watch(isUpdating, async (now, before) => {
	if (!before || now) return;
	await check();
	emit("updated");
});

onMounted(check);
</script>
