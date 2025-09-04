<template>
	<Dialog
		v-model="open"
		:options="{
			title: 'Import Standard Page',
			size: 'lg',
		}">
		<template #body-content>
			<div class="space-y-4">
				<div>
					<FormControl
						type="select"
						label="Source App"
						v-model="selectedApp"
						:options="appOptions"
						placeholder="Select an app"></FormControl>
					<p class="mt-1 text-sm text-gray-600">Choose which app contains the standard page</p>
				</div>

				<div v-if="selectedApp">
					<FormControl
						type="select"
						label="Standard Page"
						v-model="selectedPage"
						:options="standardPageOptions"
						placeholder="Select a standard page"></FormControl>
					<p class="mt-1 text-sm text-gray-600">Available standard pages in {{ selectedApp }}</p>
				</div>

				<div v-if="selectedPage">
					<FormControl
						type="text"
						label="New Page Name (Optional)"
						v-model="newPageName"
						placeholder="Enter name for the new page"></FormControl>
					<p class="mt-1 text-sm text-gray-600">
						If empty, the original page name will be used with "Copy" suffix
					</p>
				</div>

				<div v-if="selectedPage" class="rounded-lg bg-green-50 p-4">
					<h3 class="mb-2 text-sm font-medium text-green-900">Import Process:</h3>
					<ul class="space-y-1 text-sm text-green-800">
						<li>Creates a new Builder Page from the standard configuration</li>
						<li>Imports associated client scripts</li>
						<li>Preserves all styling and layout</li>
						<li>Page will be created as unpublished</li>
					</ul>
				</div>
			</div>
		</template>
		<template #actions>
			<Button
				variant="solid"
				:loading="importing"
				:disabled="!selectedApp || !selectedPage"
				@click="importPage">
				Import Page
			</Button>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import usePageStore from "@/stores/pageStore";
import { createResource } from "frappe-ui";
import { computed, ref, watch } from "vue";
import { toast } from "vue-sonner";

interface Props {
	modelValue: boolean;
}

interface Emits {
	(e: "update:modelValue", value: boolean): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const pageStore = usePageStore();

const open = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
});

const selectedApp = ref("");
const selectedPage = ref("");
const newPageName = ref("");
const importing = ref(false);

// Fetch available apps
const appsResource = createResource({
	url: "builder.api.get_apps_for_export",
	auto: true,
});

const appOptions = computed(() => {
	if (!appsResource.data) return [];
	return appsResource.data.map((app: any) => ({
		label: app.title,
		value: app.name,
	}));
});

// Mock standard page options - in real implementation, this would
// scan the app directories for builder_files/pages
const standardPagesResource = createResource({
	url: "builder.api.get_standard_pages",
});

const standardPageOptions = computed(() => {
	if (!selectedApp.value || !standardPagesResource.data) return [];
	return standardPagesResource.data.map((page: any) => ({
		label: `${page.page_title || page.page_name} (${page.folder_name})`,
		value: page.folder_name,
	}));
});

// Watch for app changes to fetch standard pages
watch(selectedApp, (newApp) => {
	selectedPage.value = "";
	if (newApp) {
		standardPagesResource.submit({ app_name: newApp });
	}
});

const importPage = async () => {
	if (!selectedApp.value || !selectedPage.value) {
		toast.error("Please select both app and page");
		return;
	}

	importing.value = true;
	try {
		await pageStore.duplicateStandardPage(
			selectedApp.value,
			selectedPage.value,
			newPageName.value || undefined,
		);
		open.value = false;
		// Reset form
		selectedApp.value = "";
		selectedPage.value = "";
		newPageName.value = "";
	} finally {
		importing.value = false;
	}
};

// Reset form when dialog opens
watch(open, (isOpen) => {
	if (isOpen) {
		selectedApp.value = "";
		selectedPage.value = "";
		newPageName.value = "";
	}
});

// Reset page selection when app changes
watch(selectedApp, () => {
	selectedPage.value = "";
});
</script>
