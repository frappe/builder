<template>
	<!-- one field and two buttons. The default "lg" size is too wide -->
	<Dialog v-model="showDevExtensionDialog" title="Load Dev Extension" size="sm">
		<template #default>
			<p class="text-p-sm text-ink-gray-6">
				The address of the dev server running the extension. It runs until you reload the editor.
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
				<Button variant="subtle" @click="showDevExtensionDialog = false">Cancel</Button>
				<Button variant="solid" :loading="loading" @click="load">Load</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import { loadExtensions } from "@/data/extensions";
import { lastDevUrl, loadDevExtension, showDevExtensionDialog } from "@/extensions/devExtension";
import { Button, FormControl, toast } from "frappe-ui";
import { ref, watch } from "vue";

const url = ref(lastDevUrl());
const error = ref("");
const loading = ref(false);

// the dialog fills the field each time it opens. So a reload needs only one click
watch(showDevExtensionDialog, (open) => {
	if (!open) return;
	url.value = lastDevUrl();
	error.value = "";
});

const load = async () => {
	loading.value = true;
	error.value = "";
	try {
		const extension = await loadDevExtension(url.value);
		// the panel opens the new record. So the list must name it
		await loadExtensions();
		showDevExtensionDialog.value = false;
		toast.success(`Loaded ${extension.label}`, {
			description: extension.permissions.length
				? `Granted ${extension.permissions.join(", ")}`
				: "It asked for no permissions",
		});
	} catch (thrown) {
		error.value = (thrown as Error).message;
	} finally {
		loading.value = false;
	}
};
</script>
