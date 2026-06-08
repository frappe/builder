<template>
	<Dialog v-model="showTemplatesDialog" size="5xl" bare>
		<template #default>
			<DialogTitle class="sr-only">Create a new page</DialogTitle>
			<DialogDescription class="sr-only">
				Start from a blank page or pick a page from a template.
			</DialogDescription>
			<div class="relative flex max-h-[85vh] min-h-[560px] flex-col overflow-hidden bg-surface-white">
				<!-- header -->
				<div class="px-8 pb-4 pt-7">
					<Button
						v-if="activeGroup"
						icon-left="lucide-arrow-left"
						variant="ghost"
						class="-ml-2 mb-3 !text-ink-gray-6 hover:!text-ink-gray-9"
						@click="selectedGroup = ''">
						Back to all templates
					</Button>
					<div class="mb-2 flex flex-col gap-2">
						<h2 class="text-xl font-semibold leading-none text-ink-gray-9">{{ heading }}</h2>
						<p class="max-w-2xl text-sm leading-relaxed text-ink-gray-5" v-if="activeGroup?.description">
							{{ activeGroup.description }}
						</p>
						<p class="text-p-sm text-ink-gray-5" v-else-if="!activeGroup">
							Start from a blank page or pick a template.
						</p>
					</div>
				</div>
				<Button
					icon="lucide-x"
					variant="subtle"
					class="absolute right-5 top-5"
					@click="showTemplatesDialog = false"></Button>

				<!-- pages within the selected group -->
				<TemplatePageGrid
					v-if="activeGroup"
					:group="activeGroup"
					:loading="Boolean(templateGroups.loading)"
					@select="useTemplate"
					@edit="editTemplate"></TemplatePageGrid>

				<!-- gallery: blank page + a preview card per template group -->
				<div v-else class="no-scrollbar flex-1 overflow-y-auto px-8 pb-8">
					<div v-if="templateGroups.loading && !groups.length" class="grid gap-3 auto-fill-[190px]">
						<div v-for="i in 6" :key="i" class="flex flex-col gap-2">
							<div class="aspect-video w-full animate-pulse rounded-lg bg-surface-gray-2"></div>
							<div class="h-3.5 w-2/3 animate-pulse rounded bg-surface-gray-2"></div>
						</div>
					</div>
					<div v-else class="grid gap-x-4 gap-y-5 auto-fill-[190px]">
						<button
							class="flex aspect-video w-full flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-outline-gray-3 text-ink-gray-5 transition-colors duration-150 hover:border-outline-gray-4 hover:bg-surface-gray-1 hover:text-ink-gray-7"
							@click="createBlankPage">
							<PlusIcon class="size-5" />
							<span class="text-sm">Blank page</span>
						</button>
						<TemplateGroupCard
							v-for="group in groups"
							:key="group.name"
							:group="group"
							@select="(group: TemplateGroup) => (selectedGroup = group.name)"></TemplateGroupCard>
					</div>
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
import PlusIcon from "~icons/lucide/plus";
import TemplateGroupCard from "./TemplateGroupCard.vue";
import TemplatePageGrid from "./TemplatePageGrid.vue";

const { showTemplatesDialog, lastTemplateGroup } = useDashboardState();
const builderStore = useBuilderStore();
const pageStore = usePageStore();

// "" = top-level gallery; a group name = drilled into that group's pages.
// persisted so reopening the picker lands on the last template you viewed.
const selectedGroup = lastTemplateGroup;

const groups = computed<TemplateGroup[]>(() => templateGroups.data || []);
const activeGroup = computed<TemplateGroup | null>(
	() => groups.value.find((group) => group.name === selectedGroup.value) || null,
);
const heading = computed(() => activeGroup.value?.title || "New page");

watch(showTemplatesDialog, (open) => {
	// revalidate on open — the cache (IndexedDB-backed) renders instantly
	// but goes stale when new template groups are synced on migrate
	if (open && !templateGroups.loading) {
		templateGroups.fetch();
	}
});

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
