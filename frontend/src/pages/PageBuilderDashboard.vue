<template>
	<div class="flex h-screen">
		<DashboardSidebar></DashboardSidebar>
		<div class="flex w-full flex-1 flex-col overflow-hidden">
			<DashboardToolbar class="sticky top-0" />
			<DashboardContent />
		</div>
	</div>
</template>
<script setup lang="ts">
import DashboardContent from "@/components/DashboardContent.vue";
import DashboardSidebar from "@/components/DashboardSidebar.vue";
import DashboardToolbar from "@/components/DashboardToolbar.vue";
</script>
