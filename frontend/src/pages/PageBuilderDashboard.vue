<template>
	<div class="flex h-screen">
		<DashboardSidebar></DashboardSidebar>
		<div class="flex w-full flex-1 flex-col overflow-hidden">
			<DashboardToolbar class="sticky top-0" />
			<DashboardHead />
			<DashboardContent />
		</div>
	</div>
	<BuilderCommandPalette />
	<TemplatesDialog />
</template>
<script setup lang="ts">
import BuilderCommandPalette from "@/components/BuilderCommandPalette.vue";
import DashboardContent from "@/components/DashboardContent.vue";
import DashboardHead from "@/components/DashboardHead.vue";
import DashboardSidebar from "@/components/DashboardSidebar.vue";
import DashboardToolbar from "@/components/DashboardToolbar.vue";
import TemplatesDialog from "@/components/Templates/TemplatesDialog.vue";
import { builderSettings } from "@/data/builderSettings";
import router, { sessionUser } from "@/router";
import { prefetchBuilderSettings, prefetchTemplateGallery } from "@/utils/prefetch";
import { onMounted, watch } from "vue";

onMounted(() => {
	prefetchBuilderSettings();
	prefetchTemplateGallery();
});
// The survey runs on Frappe Cloud sites only; ?persona_survey=test forces the redirect elsewhere.
const devForceShow = new URLSearchParams(window.location.search).get("persona_survey") === "test";

watch(
	[() => builderSettings.doc, sessionUser],
	() => {
		if (window.is_fc_site !== "True" && !devForceShow) return;
		if (!builderSettings.doc) return;
		if (builderSettings.doc.persona_survey_done && !devForceShow) return;
		if (!sessionUser.value || sessionUser.value === "Guest") return;
		router.replace({
			name: "persona-survey",
			query: devForceShow ? { persona_survey: "test" } : {},
		});
	},
	{ immediate: true },
);
</script>
