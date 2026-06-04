<template>
	<Dialog v-model="showTemplatesDialog" size="5xl" bare>
		<template #default>
			<DialogTitle class="sr-only">Create a new page</DialogTitle>
			<DialogDescription class="sr-only">
				Start from a blank page or pick a page from a template.
			</DialogDescription>
			<div
				class="flex h-[85vh] max-h-[750px] overflow-hidden rounded-xl dark:border dark:border-outline-gray-2">
				<TemplateGroupList :groups="groups" v-model="selectedGroup"></TemplateGroupList>
				<div class="relative flex flex-1 flex-col overflow-hidden bg-surface-white">
					<div class="flex flex-col gap-1 p-5 pb-2">
						<h2 class="text-lg font-semibold text-ink-gray-9">{{ heading }}</h2>
						<p class="text-p-sm text-ink-gray-5" v-if="activeGroup?.description">
							{{ activeGroup.description }}
						</p>
					</div>
					<Button
						icon="lucide-x"
						variant="ghost"
						class="absolute right-4 top-4"
						@click="showTemplatesDialog = false"></Button>
					<TemplatePageGrid
						:group="activeGroup"
						:blank="selectedGroup === BLANK_GROUP"
						:loading="Boolean(templateGroups.loading)"
						@blank="createBlankPage"
						@select="useTemplate"
						@edit="editTemplate"></TemplatePageGrid>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import { useDashboardState } from "@/composables/useDashboardState";
import { templateGroups } from "@/data/webPage";
import router from "@/router";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { TemplateGroup, TemplatePageSummary } from "@/types/doctypes";
import { createResource, toast } from "frappe-ui";
import { DialogDescription, DialogTitle } from "reka-ui";
import { computed, ref, watch } from "vue";
import TemplateGroupList from "./TemplateGroupList.vue";
import TemplatePageGrid from "./TemplatePageGrid.vue";
import { BLANK_GROUP } from "./templateDialogState";

const { showTemplatesDialog } = useDashboardState();
const builderStore = useBuilderStore();
const pageStore = usePageStore();

const selectedGroup = ref(BLANK_GROUP);

const groups = computed<TemplateGroup[]>(() => templateGroups.data || []);
const activeGroup = computed<TemplateGroup | null>(
	() => groups.value.find((group) => group.name === selectedGroup.value) || null,
);
const heading = computed(() =>
	selectedGroup.value === BLANK_GROUP ? "Blank page" : activeGroup.value?.title || "Templates",
);

watch(showTemplatesDialog, (open) => {
	// always revalidate on open — the cache (IndexedDB-backed) renders instantly
	// but goes stale when new template groups are synced on migrate
	if (open && !templateGroups.loading) {
		templateGroups.fetch();
	}
});

// land on the first template group once available
watch(
	groups,
	(value) => {
		if (value.length && selectedGroup.value === BLANK_GROUP) {
			selectedGroup.value = value[0].name;
		}
	},
	{ immediate: true },
);

const createBlankPage = () => {
	showTemplatesDialog.value = false;
	router.push({ name: "builder", params: { pageId: "new" } });
};

const creatingPage = ref(false);
const useTemplate = (page: TemplatePageSummary) => {
	if (creatingPage.value) return;
	creatingPage.value = true;
	const promise = createResource({
		url: "builder.api.create_page_from_template",
	})
		.submit({
			template_page: page.name,
			project_folder: builderStore.activeFolder || undefined,
		})
		.then((newPageName: string) => {
			showTemplatesDialog.value = false;
			router.push({ name: "builder", params: { pageId: newPageName }, force: true });
			pageStore.setPage(newPageName);
		});
	toast.promise(promise, {
		loading: "Creating page from template...",
		success: () => "Page created",
		error: () => "Could not create page from template",
	});
	promise.finally(() => {
		creatingPage.value = false;
	});
};

const editTemplate = (page: TemplatePageSummary) => {
	showTemplatesDialog.value = false;
	router.push({ name: "builder", params: { pageId: page.name } });
};
</script>
