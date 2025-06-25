<template>
	<div class="no-scrollbar flex h-full flex-col items-center gap-6 overflow-y-auto px-[2px]">
		<div class="flex w-full gap-4">
			<div class="flex flex-1 flex-col gap-6">
				<div class="flex gap-5">
					<BuilderInput
						type="text"
						label="Page Title"
						:modelValue="pageStore.activePage?.page_title"
						:hideClearButton="true"
						@update:modelValue="(val: string) => pageStore.updateActivePage('page_title', val)" />
					<BuilderInput
						type="text"
						label="Page Route"
						class="[&>p]:text-p-xs"
						:modelValue="pageStore.activePage?.route"
						:hideClearButton="true"
						@update:modelValue="(val: string) => pageStore.updateActivePage('route', val)" />
				</div>
				<div class="flex flex-col gap-3 text-base">
					<div class="flex">
						<span class="w-20 text-ink-gray-6">URL</span>
						<a class="font-medium text-ink-gray-8 hover:underline" target="_blank" :href="fullURL">
							{{ fullURL }}
						</a>
					</div>
					<div class="flex items-center">
						<span class="w-20 text-ink-gray-6">Status</span>
						<div class="flex items-center gap-2">
							<span class="flex items-center gap-2 text-base text-ink-gray-9">
								<FeatherIcon
									name="check-circle"
									class="size-4 text-ink-green-3"
									v-if="pageStore.activePage?.published && !pageStore.activePage.authenticated_access" />
								<AuthenticatedUserIcon
									class="size-4 text-ink-amber-3"
									v-else-if="
										pageStore.activePage?.published && pageStore.activePage?.authenticated_access
									"></AuthenticatedUserIcon>
								<FeatherIcon
									name="alert-circle"
									class="size-4 text-ink-gray-4"
									v-else-if="!pageStore.activePage?.published" />
								{{
									pageStore.activePage?.published
										? pageStore.activePage?.authenticated_access
											? "Published with limited access"
											: "Published"
										: "Draft"
								}}
							</span>

							<BuilderButton
								variant="subtle"
								@click="
									pageStore.activePage?.published ? pageStore.unpublishPage() : pageStore.publishPage(false)
								">
								{{ pageStore.activePage?.published ? "Unpublish" : "Publish" }}
							</BuilderButton>
						</div>
					</div>
				</div>
				<!-- favicon -->
				<hr class="w-full border-outline-gray-2" />

				<div class="flex flex-col justify-between gap-5">
					<span class="text-lg font-semibold text-ink-gray-9">Favicon</span>
					<div class="flex flex-1 gap-5">
						<div
							class="flex items-center justify-center rounded border border-outline-gray-1 bg-surface-gray-2 px-20 py-5">
							<img
								:src="
									pageStore.activePage?.favicon ||
									builderSettings.doc?.favicon ||
									'/assets/builder/images/frappe_black.png'
								"
								alt="Favicon"
								class="size-6 rounded" />
						</div>
						<div class="flex flex-1 flex-col gap-2">
							<ImageUploader
								label="Favicon"
								image_type="image/ico"
								:image_url="pageStore.activePage?.favicon"
								@upload="(url: string) => pageStore.updateActivePage('favicon', url)"
								@remove="() => pageStore.updateActivePage('favicon', '')" />
							<span class="text-p-sm text-ink-gray-6">
								Appears next to the title in your browser tab. Recommended size is 32x32 px in PNG or ICO
							</span>
						</div>
					</div>
				</div>
				<div class="flex flex-col gap-4">
					<hr class="w-full border-outline-gray-2" />
					<!-- homepage -->
					<div class="flex items-center justify-between">
						<div class="flex flex-col gap-2">
							<span class="text-base font-medium text-ink-gray-9">Homepage</span>
							<p class="text-base text-ink-gray-5">Set current page as Homepage</p>
						</div>
						<BuilderButton
							variant="subtle"
							@click="
								() => {
									if (pageStore.isHomePage(pageStore.activePage)) {
										builderStore.unsetHomePage();
									} else {
										builderStore.setHomePage(pageStore.activePage?.route as string);
									}
								}
							">
							{{ pageStore.isHomePage(pageStore.activePage) ? "Unset Homepage" : "Set As Homepage" }}
						</BuilderButton>
					</div>
					<hr class="w-full border-outline-gray-2" />
					<Switch
						size="sm"
						label="Protected Page"
						:disabled="pageStore.isHomePage(pageStore.activePage)"
						description="Only logged-in users can access this page"
						:modelValue="Boolean(pageStore.activePage?.authenticated_access)"
						@update:modelValue="(val: Boolean) => pageStore.updateActivePage('authenticated_access', val)" />
					<hr class="w-full border-outline-gray-2" />
					<Switch
						size="sm"
						label="Disable Indexing"
						description="Prevent search engines from indexing this page"
						:modelValue="Boolean(pageStore.activePage?.disable_indexing)"
						@update:modelValue="(val: Boolean) => pageStore.updateActivePage('disable_indexing', val)" />
					<hr class="w-full border-outline-gray-2" />
					<div class="flex items-center justify-between">
						<div class="flex flex-col gap-2">
							<span class="text-base font-medium text-ink-gray-9">Folder</span>
							<p class="text-base text-ink-gray-5">Set folder to organize your page</p>
						</div>
						<div>
							<BuilderInput
								class="w-fit"
								type="select"
								:options="folderOptions"
								:modelValue="pageStore.activePage?.project_folder"
								@update:modelValue="
									(val: string) => pageStore.updateActivePage('project_folder', val)
								"></BuilderInput>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import ImageUploader from "@/components/Controls/ImageUploader.vue";
import Switch from "@/components/Controls/Switch.vue";
import AuthenticatedUserIcon from "@/components/Icons/AuthenticatedUser.vue";
import builderProjectFolder from "@/data/builderProjectFolder";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { BuilderProjectFolder } from "@/types/Builder/BuilderProjectFolder";
import { FeatherIcon } from "frappe-ui";
import { computed } from "vue";

const pageStore = usePageStore();
const builderStore = useBuilderStore();
const fullURL = computed(
	() => window.location.origin + (pageStore.activePage?.route ? "/" + pageStore.activePage.route : ""),
);

const folderOptions = computed(() => {
	const homeOption = {
		label: "Home",
		value: "",
	};

	const options = builderProjectFolder.data.map((folder: BuilderProjectFolder) => {
		return {
			label: folder.folder_name,
			value: folder.folder_name,
		};
	});

	return [homeOption, ...options];
});
</script>
