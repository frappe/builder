<template>
	<div class="flex flex-col gap-5">
		<ol v-if="steps.length" class="m-0 flex list-none flex-col gap-2.5 p-0">
			<li v-for="(text, index) in steps" :key="index" class="flex items-start gap-2.5 text-p-sm">
				<LoadingIndicator
					v-if="running && index === steps.length - 1"
					class="mt-0.5 size-4 shrink-0 text-ink-gray-6" />
				<LucideCheck v-else class="mt-0.5 size-4 shrink-0 text-ink-gray-4" />
				<span :class="running && index === steps.length - 1 ? 'text-ink-gray-8' : 'text-ink-gray-5'">
					{{ text }}
				</span>
			</li>
		</ol>
		<Button
			v-if="done"
			variant="solid"
			size="md"
			class="w-full"
			:label="__('Open your pages')"
			@click="emit('open')" />
		<Button
			v-else-if="failed"
			variant="solid"
			size="md"
			class="w-full"
			:label="__('Try again')"
			@click="emit('retry')" />
		<Button
			v-else
			variant="subtle"
			size="md"
			class="w-full"
			:label="__('Look around meanwhile')"
			@click="emit('open')" />
	</div>
</template>

<script setup lang="ts">
import { useSiteClone } from "@/composables/useSiteClone";
import { __ } from "@/translation";
import { Button, LoadingIndicator } from "frappe-ui";
import { computed } from "vue";
import LucideCheck from "~icons/lucide/check";

const SHOWN_STEPS = 5;
const emit = defineEmits<{ open: []; retry: [] }>();
const { clone, done, failed, running } = useSiteClone();
const steps = computed(() => (clone.value?.events ?? []).map((event) => event.text).slice(-SHOWN_STEPS));
</script>
