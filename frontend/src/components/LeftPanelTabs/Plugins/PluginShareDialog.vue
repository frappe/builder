<template>
	<!-- Sharing runs Bob's code for every editor of the site, so the code is on the page, not behind a link -->
	<Dialog
		:modelValue="open"
		size="lg"
		bare
		@update:modelValue="(value: boolean) => emit('update:open', value)">
		<div class="flex flex-col gap-3 bg-surface-elevation-2 p-5">
			<DialogTitle as="h3" class="text-md-semibold text-ink-gray-9">
				{{ isUpdate ? `Share the update to ${label}?` : `Share ${label}?` }}
			</DialogTitle>
			<p class="text-p-sm text-ink-gray-6">
				Everyone who edits this site gets it the next time they open the editor. It runs with each person's
				own access, so read what it does first.
			</p>

			<div class="flex flex-col gap-1">
				<span class="text-xs text-ink-gray-5">main.js</span>
				<div v-if="code === null" class="rounded flex h-24 items-center justify-center bg-surface-gray-1">
					<LoadingIndicator class="size-4 text-ink-gray-5" />
				</div>
				<pre
					v-else
					class="rounded max-h-72 overflow-auto bg-surface-gray-1 p-3 font-mono text-xs leading-5 text-ink-gray-7"
					>{{ code }}</pre
				>
			</div>

			<div class="flex justify-end gap-2 pt-1">
				<Button variant="subtle" label="Cancel" @click="emit('update:open', false)" />
				<Button
					variant="solid"
					icon-left="lucide-users"
					:label="isUpdate ? 'Share update' : 'Share'"
					:disabled="code === null"
					@click="emit('share')" />
			</div>
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import { getPluginCode } from "@/data/plugins";
import { Button, LoadingIndicator } from "frappe-ui";
import { DialogTitle } from "reka-ui";
import { ref, watch } from "vue";

const props = defineProps<{ open: boolean; plugin: string; label: string; isUpdate: boolean }>();

const emit = defineEmits<{ "update:open": [open: boolean]; share: [] }>();

const code = ref<string | null>(null);

watch(
	() => props.open,
	async (open) => {
		if (!open) return;
		code.value = null;
		code.value = (await getPluginCode(props.plugin)) ?? "";
	},
	{ immediate: true },
);
</script>
