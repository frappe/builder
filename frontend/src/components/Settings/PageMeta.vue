<template>
	<div class="no-scrollbar flex h-full w-full flex-col items-center gap-5 overflow-y-auto">
		<div class="flex w-full gap-5">
			<!-- meta -->
			<div class="flex flex-1 flex-col gap-4">
				<div class="flex flex-1 flex-col gap-4">
					<Input
						type="text"
						label="Title"
						:modelValue="store.activePage?.page_title"
						@update:modelValue="(val: string) => store.updateActivePage('page_title', val)" />
					<Input
						type="textarea"
						label="Description"
						:modelValue="store.activePage?.meta_description"
						:hideClearButton="true"
						@update:modelValue="(val: string) => store.updateActivePage('meta_description', val)" />
				</div>
				<div class="flex flex-1 flex-col justify-between gap-2">
					<ImageUploadInput
						:imageURL="store.activePage?.meta_image"
						label="Meta Image"
						placeholder="Upload Meta Image"
						labelPosition="top"
						description="Recommended size: 1200 x 630 px; Page preview image is used as a fallback if Meta Image is not set"
						@update:imageURL="(url: string) => store.updateActivePage('meta_image', url)"></ImageUploadInput>
				</div>
			</div>
			<!-- preview -->
			<div class="flex h-fit w-72 flex-shrink-0 flex-col justify-between gap-1">
				<span class="text-sm text-text-icons-gray-5">Social Preview</span>
				<div class="flex flex-1 flex-col rounded border border-outline-gray-2">
					<img
						:src="store.activePage?.meta_image || store.activePage?.preview"
						alt=""
						class="h-40 w-full rounded-t object-cover" />
					<div class="flex flex-1 flex-col gap-1 border-t border-outline-gray-2 p-2">
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
		</div>
		<hr class="w-full border-surface-gray-2" />
		<div class="flex w-full flex-col justify-between gap-3">
			<span class="text-lg font-semibold text-text-icons-gray-9">Custom Meta Tags</span>
			<ListView class="h-[150px]" :columns="[]" :rows="[]" />
		</div>
	</div>
</template>
<script setup lang="ts">
import ImageUploadInput from "@/components/ImageUploadInput.vue";
import useStore from "@/store";
import { ListView } from "frappe-ui";
// check route for page id
const store = useStore();
</script>
