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
	<GenerateSiteDialog />
</template>
<script setup lang="ts">
import BuilderCommandPalette from "@/components/BuilderCommandPalette.vue";
import DashboardContent from "@/components/DashboardContent.vue";
import DashboardHead from "@/components/DashboardHead.vue";
import DashboardSidebar from "@/components/DashboardSidebar.vue";
import DashboardToolbar from "@/components/DashboardToolbar.vue";
import GenerateSiteDialog from "@/components/Site/GenerateSiteDialog.vue";
import TemplatesDialog from "@/components/Templates/TemplatesDialog.vue";
import { builderSettings } from "@/data/builderSettings";
import router, { sessionUser } from "@/router";
import { useTelemetry } from "frappe-ui/frappe";
import { watch } from "vue";

const telemetry = useTelemetry();
// Dev benches have telemetry (and thus the survey) off; ?persona_survey=test forces the redirect.
const devForceShow = new URLSearchParams(window.location.search).get("persona_survey") === "test";

watch(
	[() => telemetry.isEnabled, () => builderSettings.doc, sessionUser],
	() => {
		if (!telemetry.isEnabled && !devForceShow) return;
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
