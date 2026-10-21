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
import {
	getExtensionUpdate,
	updateFromHub,
	updatingExtensions,
	type ExtensionUpdate,
} from "@/data/extensions";
import { Button, toast } from "frappe-ui";
import { computed, onMounted, shallowRef, watch } from "vue";

const props = defineProps<{ extension: string }>();
/** The details page reloads its README. */
const emit = defineEmits<{ updated: [] }>();

const update = shallowRef<ExtensionUpdate | null>(null);
/** Shared, so a return to this page while the job runs still shows it. */
const isUpdating = computed(() => updatingExtensions.has(props.extension));

/** A Hub that is down only hides the offer. The installed release still runs. */
const check = async () => {
	try {
		update.value = await getExtensionUpdate(props.extension);
	} catch (error) {
		console.warn(`Could not check "${props.extension}" for an update`, error);
	}
};

const start = async () => {
	try {
		await updateFromHub(props.extension, update.value!.version);
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
