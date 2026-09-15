<template>
	<Badge v-if="page.published" theme="green" size="sm">
		{{ __("Live") }}
	</Badge>
	<Badge v-else-if="page.staging" theme="violet" size="sm">
		{{ __("Staging") }}
	</Badge>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import { BuilderPage } from "@/types/doctypes";
import { Badge } from "frappe-ui";

defineProps<{
	page: BuilderPage;
}>();
</script>
