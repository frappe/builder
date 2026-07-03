<template>
	<div class="flex h-full flex-col overflow-hidden">
		<!-- header -->
		<div class="px-8 pb-4 pr-5 pt-7">
			<Button
				v-if="activeGroup"
				icon-left="lucide-arrow-left"
				variant="ghost"
				class="-ml-3 mb-5"
				@click="selectedGroup = ''">
				Back to all templates
			</Button>
			<div class="mb-2 flex flex-col gap-2">
				<div class="flex items-center justify-between">
					<h2 class="text-3xl-semibold leading-none text-ink-gray-9">{{ heading }}</h2>
					<Button
						v-if="activeGroup"
						variant="outline"
						:loading="importingAll"
						icon-left="lucide-copy-plus"
						@click="importAll">
						Use all {{ activeGroup?.pages.length }} pages
					</Button>
				</div>
				<p v-if="activeGroup?.description" class="max-w-2xl text-sm leading-relaxed text-ink-gray-5">
					{{ activeGroup.description }}
				</p>
				<p v-else-if="!activeGroup" class="text-p-sm text-ink-gray-5">
					{{ props.subtitle }}
				</p>
			</div>
		</div>

		<!-- pages within the selected group -->
		<TemplatePageGrid
			v-if="activeGroup"
			:group="activeGroup"
			:loading="Boolean(templateGroups.loading)"
			@select="useTemplate"
			@blank="createBlankPage('template_group')"
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
					class="flex w-full flex-col self-start rounded-lg border border-dashed border-outline-gray-3 p-1.5 text-ink-gray-5 transition-colors duration-150 hover:border-outline-gray-4 hover:bg-surface-gray-1 hover:text-ink-gray-7"
					@click="createBlankPage('gallery')">
					<span class="flex aspect-video w-full flex-col items-center justify-center gap-2">
						<PlusIcon class="size-5" />
						<span class="text-sm">Start from scratch</span>
					</span>
				</button>
				<TemplateGroupCard
					v-for="group in visibleGroups"
					:key="group.name"
					:group="group"
					@select="(group: TemplateGroup) => (selectedGroup = group.name)"></TemplateGroupCard>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useDashboardState } from "@/composables/useDashboardState";
import router from "@/router";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { templateGroups, webPages } from "@/data/webPage";
import { TemplateGroup, TemplatePageSummary } from "@/types/template";
import { Button, createResource, toast } from "frappe-ui";
import { useTelemetry } from "frappe-ui/frappe";
import { computed, onMounted, ref } from "vue";
import PlusIcon from "~icons/lucide/plus";
import TemplateGroupCard from "./TemplateGroupCard.vue";
import TemplatePageGrid from "./TemplatePageGrid.vue";

const props = withDefaults(
	defineProps<{
		heading?: string;
		subtitle?: string;
		// cap the number of template groups shown (0 = show all); the blank tile is extra
		maxGroups?: number;
	}>(),
	{
		heading: "New page",
		subtitle: "Start from a blank page or pick a template.",
		maxGroups: 0,
	},
);

const { showTemplatesDialog, lastTemplateGroup } = useDashboardState();
const builderStore = useBuilderStore();
const pageStore = usePageStore();
const { capture } = useTelemetry();

// "" = top-level gallery; a group name = drilled into that group's pages.
// persisted so reopening the picker lands on the last template you viewed.
const selectedGroup = lastTemplateGroup;

const groups = computed<TemplateGroup[]>(() => templateGroups.data || []);
const visibleGroups = computed<TemplateGroup[]>(() =>
	props.maxGroups > 0 ? groups.value.slice(0, props.maxGroups) : groups.value,
);
const activeGroup = computed<TemplateGroup | null>(
	() => groups.value.find((group) => group.name === selectedGroup.value) || null,
);
const heading = computed(() => activeGroup.value?.title || props.heading);

onMounted(() => {
	// revalidate on mount — the cache (IndexedDB-backed) renders instantly
	// but goes stale when new template groups are synced on migrate
	if (!templateGroups.loading) {
		templateGroups.fetch();
	}
});

const createBlankPage = (source: "gallery" | "template_group" = "gallery") => {
	capture("builder_blank_page_selected", { source });
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
			capture("builder_page_template_used", {
				template_page: page.name,
				template_group: page.template_group,
				source: page.live_url ? "hub" : "local",
			});
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

const importingAll = ref(false);
const importAll = () => {
	if (importingAll.value || !activeGroup.value) return;
	importingAll.value = true;
	const promise = createResource({
		url: "builder.api.import_template_group",
	})
		.submit({
			template_group: activeGroup.value.name,
			project_folder: builderStore.activeFolder || undefined,
		})
		.then((pageNames: string[]) => {
			capture("builder_template_group_imported", {
				template_group: activeGroup.value!.name,
				page_count: pageNames.length,
			});
			showTemplatesDialog.value = false;
			// land on the dashboard with the freshly imported pages so the user can
			// pick which one to open (Import all creates several pages at once)
			webPages.reload();
			router.push({ name: "home" });
		});
	toast.promise(promise, {
		loading: "Adding all pages...",
		success: () => "All pages added",
		error: () => "Could not add pages",
	});
	promise.finally(() => {
		importingAll.value = false;
	});
};

const editTemplate = (page: TemplatePageSummary) => {
	showTemplatesDialog.value = false;
	router.push({ name: "builder", params: { pageId: page.name } });
};
</script>
