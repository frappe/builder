<template>
	<!-- one field and two buttons. The default "lg" size is too wide -->
	<Dialog v-model="showDevPluginDialog" title="Load Dev Plugin" size="sm">
		<template #default>
			<p class="text-p-sm text-ink-gray-6">
				The address of the dev server running the plugin. It runs in this browser tab until you stop it.
			</p>

			<FormControl
				v-model="url"
				class="pt-4"
				type="text"
				placeholder="http://localhost:5173"
				autofocus
				@keyup.enter="load" />

			<p v-if="error" class="pt-2 text-p-sm text-ink-red-6">{{ error }}</p>
		</template>
		<template #actions>
			<div class="flex justify-end gap-2">
				<Button variant="subtle" @click="showDevPluginDialog = false">Cancel</Button>
				<Button variant="solid" :loading="loading" @click="load">Load</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import { reloadInstallations } from "@/data/plugins";
import { lastDevUrl, loadDevPlugin, showDevPluginDialog } from "@/plugins/devPlugin";
import { Button, FormControl, toast } from "frappe-ui";
import { ref, watch } from "vue";

const url = ref(lastDevUrl());
const error = ref("");
const loading = ref(false);

// the dialog fills the field each time it opens. So a reload needs only one click
watch(showDevPluginDialog, (open) => {
	if (!open) return;
	url.value = lastDevUrl();
	error.value = "";
});

const load = async () => {
	loading.value = true;
	error.value = "";
	try {
		const plugin = await loadDevPlugin(url.value);
		// the panel opens the new record. So the list must name it
		await reloadInstallations();
		showDevPluginDialog.value = false;
		toast.success(`Loaded ${plugin.label}`);
	} catch (thrown) {
		error.value = (thrown as Error).message;
	} finally {
		loading.value = false;
	}
};
</script>
