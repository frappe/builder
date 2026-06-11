<template>
	<div class="flex h-screen">
		<DashboardSidebar></DashboardSidebar>
		<div class="flex w-full flex-1 flex-col overflow-hidden pb-10">
			<DashboardToolbar class="sticky top-0" />
			<DashboardHead />
			<DashboardContent />
		</div>
	</div>
	<BuilderCommandPalette />
	<TemplatesDialog />
	<PersonaSurveyDialog />
</template>
<script setup lang="ts">
import BuilderCommandPalette from "@/components/BuilderCommandPalette.vue";
import DashboardContent from "@/components/DashboardContent.vue";
import DashboardHead from "@/components/DashboardHead.vue";
import DashboardSidebar from "@/components/DashboardSidebar.vue";
import DashboardToolbar from "@/components/DashboardToolbar.vue";
import PersonaSurveyDialog from "@/components/PersonaSurveyDialog.vue";
import TemplatesDialog from "@/components/Templates/TemplatesDialog.vue";
</script>
