<template>
	<Dialog
		v-model="open"
		:options="{
			title: 'Export Page as Standard',
			size: 'lg',
		}">
		<template #body-content>
			<div class="space-y-4">
				<div>
					<FormControl
						type="select"
						label="Target App"
						v-model="selectedApp"
						:options="appOptions"
						placeholder="Select an app"></FormControl>
					<p class="mt-1 text-sm text-gray-600">Choose which app to export the standard page to</p>
				</div>

				<div>
					<FormControl
						type="text"
						label="Export Name"
						v-model="exportName"
						placeholder="Enter name for the exported page"></FormControl>
					<p class="mt-1 text-sm text-gray-600">
						This will be used as the folder name. If empty, page name will be used.
					</p>
				</div>

				<div class="rounded-lg bg-surface-gray-1 p-4">
					<h3 class="mb-2 text-sm font-medium text-ink-gray-9">What will be exported:</h3>
					<ul class="space-y-1 text-sm text-ink-gray-6">
						<li>Page configuration (blocks, styles, scripts)</li>
						<li>Assets used in the page (images, files)</li>
						<li>Client scripts</li>
						<li>Components used in the page</li>
						<li>Variables referenced</li>
					</ul>
				</div>

				<div class="rounded-lg bg-surface-gray-1 p-4">
					<h3 class="mb-2 text-sm font-medium text-ink-gray-8">Export Structure:</h3>
					<div class="font-mono text-sm text-ink-gray-4">
						{{ selectedApp }}/builder_files/
						<br />
						&nbsp;&nbsp;├── pages/{{ exportName || "page-name" }}/
						<br />
						&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;└── config.json
						<br />
						&nbsp;&nbsp;├── assets/
						<br />
						&nbsp;&nbsp;├── client_scripts/
						<br />
						&nbsp;&nbsp;├── components/
						<br />
						&nbsp;&nbsp;└── variables/
					</div>
				</div>
			</div>
		</template>
		<template #actions>
			<Button variant="solid" :loading="exporting" @click="exportPage">Export Page</Button>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { createResource } from "frappe-ui";
import { computed, ref, watch } from "vue";
import { toast } from "vue-sonner";

interface Props {
	modelValue: boolean;
	pageName?: string;
}

interface Emits {
	(e: "update:modelValue", value: boolean): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const open = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
});

const selectedApp = ref("builder");
const exportName = ref("");
const exporting = ref(false);

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

// Export page resource
const exportResource = createResource({
	url: "builder.api.export_page_as_standard",
	onSuccess: (data: { message: string }) => {
		toast.success(data.message);
		open.value = false;
		exportName.value = "";
	},
	onError: (error) => {
		toast.error("Export failed: " + error.message);
	},
});

const exportPage = async () => {
	if (!props.pageName) {
		toast.error("No page selected for export");
		return;
	}

	if (!selectedApp.value) {
		toast.error("Please select a target app");
		return;
	}

	exporting.value = true;
	try {
		await exportResource.submit({
			page_name: props.pageName,
			target_app: selectedApp.value,
			export_name: exportName.value || undefined,
		});
	} finally {
		exporting.value = false;
	}
};

// Reset form when dialog opens
watch(open, (isOpen) => {
	if (isOpen) {
		exportName.value = "";
		selectedApp.value = "builder";
	}
});
</script>
