<template>
	<div class="flex flex-col gap-4">
		<Alert v-if="notice" :theme="notice.theme" :title="notice.title" :description="notice.text" />
		<div class="flex flex-col gap-1 rounded-lg border border-outline-gray-1 bg-surface-gray-1 px-3 pb-3 pt-2">
			<div class="-mr-1.5 flex items-center justify-between gap-2">
				<span class="text-sm text-ink-gray-6">{{ __("Your description") }}</span>
				<Button
					v-if="copyable"
					variant="ghost"
					size="sm"
					:label="copied ? __('Copied') : __('Copy')"
					@click="copy" />
			</div>
			<!-- the user's own words: text only, line breaks kept -->
			<p class="whitespace-pre-line break-words text-p-base text-ink-gray-8">{{ description }}</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import type { StartNotice } from "@/utils/promptStart";
import { Alert, Button } from "frappe-ui";
import { ref } from "vue";

const props = defineProps<{ description: string; notice?: StartNotice | null; copyable?: boolean }>();

const copied = ref(false);
async function copy() {
	try {
		await navigator.clipboard.writeText(props.description);
		copied.value = true;
		setTimeout(() => (copied.value = false), 2000);
	} catch {
		// no clipboard here: the text is still on screen to select
	}
}
</script>
