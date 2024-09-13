<template>
	<div class="no-scrollbar flex h-full flex-col items-center gap-6 overflow-y-auto">
		<div class="flex w-full gap-4">
			<div class="flex flex-1 flex-col gap-4">
				<div class="flex gap-5">
					<Input
						type="text"
						label="Page Title"
						:modelValue="store.activePage?.page_title"
						:hideClearButton="true"
						@update:modelValue="(val) => store.updateActivePage('page_title', val)" />
					<Input
						type="text"
						label="Page Route"
						:modelValue="store.activePage?.route"
						:hideClearButton="true"
						@update:modelValue="(val) => store.updateActivePage('route', val)" />
				</div>
				<!-- homepage -->
				<div class="flex flex-col gap-2">
					<div class="flex items-center justify-between">
						<div class="flex flex-col gap-2">
							<span class="text-base dark:text-zinc-200">Homepage</span>
							<p class="text-sm text-gray-600">Set current page as Homepage</p>
						</div>
						<Tooltip
							:test="
								store.activePage?.published ? 'Unpublish this page' : 'This page is already unpublished'
							">
							<Button
								variant="subtle"
								class="!bg-surface-gray-2"
								@click="store.setHomePage(store.activePage?.route as string)">
								Set As Homepage
							</Button>
						</Tooltip>
					</div>
				</div>
				<hr class="w-full border-surface-gray-2" />
				<Switch
					size="sm"
					label="Authenticated Access"
					description="Only logged-in users can access this page"
					:modelValue="Boolean(store.activePage?.authenticated_access)"
					@update:modelValue="(val: Boolean) => store.updateActivePage('authenticated_access', val)" />
				<hr class="w-full border-surface-gray-2" />
				<Switch
					size="sm"
					label="Disable Indexing"
					description="Prevent search engines from indexing this page"
					:modelValue="Boolean(store.activePage?.disable_indexing)"
					@update:modelValue="(val: Boolean) => store.updateActivePage('disable_indexing', val)" />
				<hr class="w-full border-surface-gray-2" />

				<div class="flex flex-col justify-between gap-5">
					<span class="text-lg font-semibold text-text-icons-gray-9">Favicon</span>
					<div class="flex flex-1 gap-5">
						<div class="flex items-center justify-center rounded border border-outline-gray-1 px-16 py-8">
							<img
								:src="store.activePage?.favicon || '/assets/builder/images/frappe_black.png'"
								alt=""
								class="h-7 w-7 rounded" />
						</div>
						<div class="flex flex-1 flex-col gap-2">
							<ImageUploader
								label="Favicon"
								image_type="image/ico"
								:image_url="store.activePage?.favicon"
								@upload="(url: string) => store.updateActivePage('favicon', url)"
								@remove="() => store.updateActivePage('favicon', '')" />
							<span class="text-base leading-5 text-text-icons-gray-6">
								Appears next to the title in your browser tab. Recommended size is 32x32 px in PNG or ICO
							</span>
						</div>
					</div>
				</div>
				<hr class="w-full border-surface-gray-2" />
				<div class="flex flex-col justify-between gap-5">
					<span class="text-lg font-semibold text-text-icons-gray-9">Redirect</span>
					<div class="flex items-end gap-8">
						<Input
							type="text"
							label="From URL"
							:modelValue="store.activePage?.page_title"
							:hideClearButton="true"
							@update:modelValue="(val) => store.updateActivePage('page_title', val)" />
						<FeatherIcon name="arrow-right" class="h-5 w-5 text-gray-500 dark:text-zinc-200" />
						<Input
							type="text"
							label="To URL"
							:modelValue="store.activePage?.route"
							:hideClearButton="true"
							@update:modelValue="(val) => store.updateActivePage('route', val)" />
					</div>
				</div>
			</div>
		</div>
		<hr class="w-full border-surface-gray-2" />

		<div class="flex w-full flex-col gap-5">
			<span class="text-lg font-semibold text-text-icons-gray-9">Unpublish</span>
			<div class="flex items-center justify-between">
				<div class="flex flex-col gap-2">
					<p class="text-sm text-gray-600">Unpublish your page</p>
				</div>
				<Tooltip
					:test="store.activePage?.published ? 'Unpublish this page' : 'This page is already unpublished'">
					<Button variant="outline" theme="red" @click="store.unpublishPage()">Unpublish</Button>
				</Tooltip>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import ImageUploader from "@/components/Controls/ImageUploader.vue";
import Switch from "@/components/Controls/Switch.vue";
import { Tooltip } from "frappe-ui";
import useStore from "@/store";
import FeatherIcon from "frappe-ui/src/components/FeatherIcon.vue";
// check route for page id
const store = useStore();
</script>
