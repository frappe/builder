<template>
	<Badge v-if="page.published" theme="green" :size="size" class="dark:bg-green-900 dark:text-green-400">
		{{ __("Live") }}
	</Badge>
	<Badge v-else-if="page.staging" theme="amber" :size="size" class="dark:bg-amber-900 dark:text-amber-400">
		{{ __("Staging") }}
	</Badge>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import { BuilderPage } from "@/types/doctypes";
import { Badge } from "frappe-ui";

defineProps<{
	page: BuilderPage;
	size?: "sm" | "md" | "lg";
}>();
</script>
