<template>
	<div class="no-scrollbar flex h-full flex-col items-center gap-5 overflow-y-auto">
		<div class="flex w-full gap-4">
			<div class="flex flex-1 flex-col gap-4">
				<Input
					type="text"
					label="Title"
					:modelValue="store.activePage?.page_title"
					@update:modelValue="(val) => store.updateActivePage('page_title', val)" />
				<Input
					type="textarea"
					label="Description"
					:modelValue="store.activePage?.meta_description"
					:hideClearButton="true"
					@update:modelValue="(val) => store.updateActivePage('meta_description', val)" />

				<div class="flex flex-col justify-between gap-2">
					<span class="text-base text-text-icons-gray-6">Image</span>
					<div class="flex flex-1 gap-5">
						<div class="flex shrink-0 items-center justify-center rounded border border-outline-gray-1">
							<img
								:src="store.activePage?.meta_image || store.activePage?.preview"
								alt=""
								class="w-48 rounded" />
						</div>
						<div class="flex flex-1 flex-col gap-2">
							<ImageUploader
								label="Meta Image"
								image_type="image/*"
								:image_url="store.activePage?.meta_image"
								@upload="(url: string) => store.updateActivePage('meta_image', url)"
								@remove="() => store.updateActivePage('meta_image', '')" />
							<span class="text-base leading-5 text-text-icons-gray-6">
								Image appears when the site is shared on social media. Page preview image is default for all
								pages unless changed; recommended size: 1200 x 630 px.
							</span>
						</div>
					</div>
				</div>
				<div class="flex flex-col justify-between gap-3">
					<span class="text-lg font-semibold text-text-icons-gray-9">Preview</span>
					<div class="flex flex-1 flex-col rounded border border-outline-gray-2">
						<img
							:src="store.activePage?.meta_image || store.activePage?.preview"
							alt=""
							class="h-24 w-full rounded-t object-cover" />
						<div class="flex flex-1 flex-col gap-1 p-2">
							<span class="text-base text-text-icons-gray-6">{{ store.activePage?.route }}</span>
							<span class="mt-2 text-base font-medium text-text-icons-gray-9">
								{{ store.activePage?.page_title }}
							</span>
							<span class="text-base leading-5 text-text-icons-gray-6">
								{{ store.activePage?.meta_description }}
							</span>
						</div>
					</div>
				</div>
				<hr class="w-full border-surface-gray-2" />
				<div class="flex flex-col justify-between gap-3">
					<span class="text-lg font-semibold text-text-icons-gray-9">Custom Meta Tags</span>
					<ListView class="h-[150px]" :columns="[]" :rows="[]" />
				</div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import ImageUploader from "@/components/Controls/ImageUploader.vue";
import useStore from "@/store";
import { ListView } from "frappe-ui";
// check route for page id
const store = useStore();
</script>
