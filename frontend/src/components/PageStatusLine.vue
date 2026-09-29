<template>
	<div class="flex items-center gap-1.5 text-sm text-ink-gray-5">
		<PageStatusDot :page="page" />
		<span class="truncate">{{ time }}</span>
	</div>
</template>
<script setup lang="ts">
import PageStatusDot from "@/components/PageStatusDot.vue";
import { BuilderPage } from "@/types/doctypes";

defineProps<{
	page: BuilderPage;
	time: string;
}>();
</script>
