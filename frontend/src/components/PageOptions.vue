<template>
	<div>
		<div class="flex flex-row flex-wrap gap-5">
			<h3 class="mb-1 w-full text-sm font-medium text-gray-900 dark:text-zinc-300">Page Options</h3>
			<InlineInput
				label="Title"
				type="text"
				class="w-full text-sm [&>label]:w-[60%] [&>label]:min-w-[180px]"
				:modelValue="page.page_title"
				@update:modelValue="(val) => webPages.setValue.submit({ name: page.name, page_title: val })" />
			<InlineInput
				type="text"
				class="w-full text-sm [&>label]:w-[60%] [&>label]:min-w-[180px]"
				label="Route"
				:modelValue="page.route"
				@update:modelValue="(val) => webPages.setValue.submit({ name: page.name, route: val })" />

			<!-- TODO: Fix option arrangement and placements -->

			<OptionToggle
				:label="'Dynamic Route?'"
				:modelValue="page.dynamic_route ? 'Yes' : 'No'"
				@update:modelValue="
					(val) => {
						webPages.setValue.submit({ name: page.name, dynamic_route: val === 'Yes' });
						page.dynamic_route = val === 'Yes' ? 1 : 0;
					}
				"
				:options="[
					{ label: 'Yes', value: 'Yes' },
					{ label: 'No', value: 'No' },
				]"
				ß></OptionToggle>

			<!-- Dynamic Route Variables -->
			<div v-if="page.dynamic_route" class="mb-3 mt-3 w-full">
				<h3 class="text-sm font-medium text-gray-900 dark:text-zinc-300">Route Values</h3>
				<div class="mt-5 flex flex-row flex-wrap gap-5">
					<InlineInput
						v-for="(variable, index) in dynamicVariables"
						:key="index"
						type="text"
						:label="variable.replace(/_/g, ' ')"
						class="w-full text-sm"
						:modelValue="store.routeVariables[variable]"
						@update:modelValue="(val) => store.setRouteVariable(variable, val)" />
				</div>
			</div>
			<!-- favicon -->
			<InlineInput
				label="Favicon"
				type="text"
				class="w-full text-sm [&>label]:w-[60%] [&>label]:min-w-[180px]"
				:modelValue="page.favicon"
				:disabled="true"
				@update:modelValue="(val) => webPages.setValue.submit({ name: page.name, favicon: val })" />
			<div class="flex w-full justify-end">
				<FileUploader
					file-types="image/ico"
					class="text-base [&>div>button]:dark:bg-zinc-800 [&>div>button]:dark:text-zinc-200 [&>div>button]:dark:hover:bg-zinc-700"
					@success="
						(file: FileDoc) => {
							webPages.setValue.submit({ name: page.name, favicon: file.file_url }).then(() => {
								page.favicon = file.file_url;
							});
						}
					">
					<template v-slot="{ file, progress, uploading, openFileSelector }">
						<div class="flex items-center space-x-2">
							<Button @click="openFileSelector">
								{{
									uploading ? `Uploading ${progress}%` : page.favicon ? "Change Favicon" : "Upload Favicon"
								}}
							</Button>
							<Button
								v-if="page.favicon"
								@click="
									() => {
										page.favicon = '';
										webPages.setValue.submit({ name: page.name, favicon: '' });
									}
								">
								Remove
							</Button>
						</div>
					</template>
				</FileUploader>
			</div>
			<div class="mt-5 flex w-full flex-col gap-2">
				<Button
					v-if="page.published && !store.isHomePage(page)"
					@click="() => setHomePage(page)"
					class="block text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700">
					Set as Home Page
				</Button>
				<Button
					v-if="page.published && store.isHomePage(page)"
					@click="() => unsetHomePage()"
					class="block text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700">
					Unset as Home Page
				</Button>
				<Button
					v-if="page.published"
					@click="() => store.openPageInBrowser(page)"
					class="block text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700">
					View Published Page
				</Button>
				<Button
					v-if="page.published"
					@click="() => unpublishPage()"
					class="block text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700">
					Unpublish Page
				</Button>
				<hr class="my-2 dark:border-zinc-800" v-if="page.published" />
				<Button
					@click="() => store.openInDesk(page)"
					class="block text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700">
					Open in Desk
				</Button>
				<Button
					@click="() => store.openBuilderSettings()"
					class="block text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700">
					Open Builder Settings
				</Button>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import { builderSettings } from "@/data/builderSettings";
import { webPages } from "@/data/webPage";
import useStore from "@/store";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { FileUploader } from "frappe-ui";
import { computed } from "vue";
import { toast } from "vue-sonner";
import InlineInput from "./InlineInput.vue";
import OptionToggle from "./OptionToggle.vue";

type FileDoc = {
	file_url: string;
};

const store = useStore();
const props = defineProps<{
	page: BuilderPage;
}>();
const dynamicVariables = computed(() => {
	return (props.page.route?.match(/<\w+>/g) || []).map((match) => match.slice(1, -1));
});

const unpublishPage = () => {
	webPages.setValue
		.submit({
			name: props.page.name,
			published: false,
		})
		.then(() => {
			toast.success("Page unpublished");
			store.setPage(props.page.name);
			builderSettings.reload();
		});
};

const setHomePage = (page: BuilderPage) => {
	builderSettings.setValue
		.submit({
			home_page: page.route,
		})
		.then(() => {
			toast.success("Home Page set");
		});
};

const unsetHomePage = () => {
	builderSettings.setValue
		.submit({
			home_page: "",
		})
		.then(() => {
			toast.success("Home Page unset");
		});
};
</script>
