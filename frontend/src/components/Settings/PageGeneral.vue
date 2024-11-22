<template>
	<div class="no-scrollbar flex h-full flex-col items-center gap-6 overflow-y-auto">
		<div class="flex w-full gap-4">
			<div class="flex flex-1 flex-col gap-6">
				<div class="flex gap-5">
					<BuilderInput
						type="text"
						label="Page Title"
						:modelValue="store.activePage?.page_title"
						:hideClearButton="true"
						@update:modelValue="(val: string) => store.updateActivePage('page_title', val)" />
					<BuilderInput
						type="text"
						label="Page Route"
						class="[&>p]:text-p-xs"
						:modelValue="store.activePage?.route"
						:hideClearButton="true"
						@update:modelValue="(val: string) => store.updateActivePage('route', val)" />
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
									v-if="store.activePage?.published && !store.activePage.authenticated_access" />
								<AuthenticatedUserIcon
									class="size-4 text-ink-amber-3"
									v-else-if="
										store.activePage?.published && store.activePage?.authenticated_access
									"></AuthenticatedUserIcon>
								<FeatherIcon
									name="alert-circle"
									class="size-4 text-ink-gray-4"
									v-else-if="!store.activePage?.published" />
								{{
									store.activePage?.published
										? store.activePage?.authenticated_access
											? "Published with limited access"
											: "Published"
										: "Draft"
								}}
							</span>
							<Tooltip
								:text="
									store.activePage?.published ? 'Unpublish this page' : 'This page is already unpublished'
								">
								<BuilderButton
									variant="subtle"
									@click="store.activePage?.published ? store.unpublishPage() : store.publishPage(false)">
									{{ store.activePage?.published ? "Unpublish" : "Publish" }}
								</BuilderButton>
							</Tooltip>
						</div>
					</div>
				</div>
				<!-- favicon -->
				<hr class="w-full border-outline-gray-2" />

				<div class="flex flex-col justify-between gap-5">
					<span class="text-lg font-semibold text-ink-gray-9">Favicon</span>
					<div class="flex flex-1 gap-5">
						<div class="flex items-center justify-center rounded border border-outline-gray-1 px-20 py-5">
							<img
								:src="
									store.activePage?.favicon ||
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
								:image_url="store.activePage?.favicon"
								@upload="(url: string) => store.updateActivePage('favicon', url)"
								@remove="() => store.updateActivePage('favicon', '')" />
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
						<Tooltip
							:text="
								store.isHomePage(store.activePage)
									? 'Unset this page as the homepage'
									: 'Set this page as the homepage'
							">
							<Button variant="outline" @click.stop="handleClick">
								{{ store.isHomePage(store.activePage) ? "Unset Homepage" : "Set As Homepage" }}
							</Button>
						</Tooltip>
					</div>
					<hr class="w-full border-outline-gray-2" />
					<Switch
						size="sm"
						label="Protected Page"
						:disabled="store.isHomePage(store.activePage)"
						description="Only logged-in users can access this page"
						:modelValue="Boolean(store.activePage?.authenticated_access)"
						@update:modelValue="(val: Boolean) => store.updateActivePage('authenticated_access', val)" />
					<hr class="w-full border-outline-gray-2" />
					<Switch
						size="sm"
						label="Disable Indexing"
						description="Prevent search engines from indexing this page"
						:modelValue="Boolean(store.activePage?.disable_indexing)"
						@update:modelValue="(val: Boolean) => store.updateActivePage('disable_indexing', val)" />
				</div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import ImageUploader from "@/components/Controls/ImageUploader.vue";
import Switch from "@/components/Controls/Switch.vue";
import AuthenticatedUserIcon from "@/components/Icons/AuthenticatedUser.vue";
import { builderSettings } from "@/data/builderSettings";
import useStore from "@/store";
import { Button, Tooltip } from "frappe-ui";
import FeatherIcon from "frappe-ui/src/components/FeatherIcon.vue";
import { computed } from "vue";
// check route for page id

const store = useStore();
const fullURL = computed(
	() => window.location.origin + (store.activePage?.route ? "/" + store.activePage.route : ""),
);

const handleClick = () => {
	console.log("clicked");
};
</script>
