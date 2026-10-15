<template>
	<!-- a long list stays short: the first roles, then a button for the rest -->
	<div v-if="roles.length" class="pt-3">
		<p class="text-xs text-ink-gray-5">{{ label }}</p>
		<div class="flex flex-wrap items-center gap-1 pt-1.5">
			<Badge v-for="role in shown" :key="role" :label="role" :theme="theme" />
			<Button v-if="hidden" size="sm" variant="ghost" :label="`+${hidden} more`" @click="isExpanded = true" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { Badge, Button } from "frappe-ui";
import { computed, ref } from "vue";

const SHOWN = 4;

const props = defineProps<{ roles: string[]; label: string; theme: "green" | "red" }>();
const isExpanded = ref(false);
const shown = computed(() => (isExpanded.value ? props.roles : props.roles.slice(0, SHOWN)));
const hidden = computed(() => props.roles.length - shown.value.length);
</script>
