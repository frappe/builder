<template>
	<!-- The install asks the manager to trust the plugin's code, and nothing else. -->
	<Dialog
		:modelValue="open"
		size="sm"
		bare
		@update:modelValue="(value: boolean) => emit('update:open', value)">
		<div class="bg-surface-elevation-2 p-5">
			<DialogTitle as="h3" class="text-md-semibold text-ink-gray-9">Install {{ label }}?</DialogTitle>
			<p class="pt-2 text-p-sm text-ink-gray-6">
				It runs inside the editor with the access of each user who opens it. It can read and change pages and
				site data that the user can. Install only plugins that you trust.
			</p>

			<div class="flex justify-end gap-2 pt-4">
				<Button variant="subtle" label="Cancel" @click="emit('update:open', false)" />
				<Button variant="solid" label="Install" @click="emit('install')" />
			</div>
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import { Button } from "frappe-ui";
import { DialogTitle } from "reka-ui";

defineProps<{ open: boolean; label: string }>();

const emit = defineEmits<{ "update:open": [open: boolean]; install: [] }>();
</script>
