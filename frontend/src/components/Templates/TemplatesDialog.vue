<template>
	<Dialog v-model="showTemplatesDialog" size="5xl" bare>
		<template #default>
			<DialogTitle class="sr-only">Create a new page</DialogTitle>
			<DialogDescription class="sr-only">
				Start from a blank page or pick a page from a template.
			</DialogDescription>
			<div class="relative flex max-h-[85vh] min-h-[660px] flex-col overflow-hidden">
				<TemplateGallery class="min-h-0 flex-1" />
				<Button
					icon="lucide-x"
					variant="subtle"
					class="absolute right-5 top-5"
					@click="showTemplatesDialog = false"></Button>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import { useDashboardState } from "@/composables/useDashboardState";
import { Button } from "frappe-ui";
import { useTelemetry } from "frappe-ui/frappe";
import { DialogDescription, DialogTitle } from "reka-ui";
import { watch } from "vue";
import TemplateGallery from "./TemplateGallery.vue";

const { showTemplatesDialog } = useDashboardState();
const { capture } = useTelemetry();

watch(showTemplatesDialog, (open) => {
	if (!open) return;
	capture("builder_template_dialog_opened");
});
</script>
