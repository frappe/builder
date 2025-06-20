<template>
	<div class="no-scrollbar flex h-full w-full flex-col items-center gap-5 overflow-y-auto px-[2px]">
		<div class="flex w-full gap-5">
			<!-- meta -->
			<div class="flex flex-1 flex-col gap-4">
				<div class="flex flex-1 flex-col gap-4">
					<BuilderInput
						type="text"
						label="Title"
						:modelValue="pageStore.activePage?.page_title"
						@update:modelValue="(val: string) => pageStore.updateActivePage('page_title', val)" />
					<BuilderInput
						class="[&>div>textarea]:h-28"
						type="textarea"
						label="Description"
						:modelValue="pageStore.activePage?.meta_description"
						:hideClearButton="true"
						@update:modelValue="(val: string) => pageStore.updateActivePage('meta_description', val)" />
				</div>
				<div class="flex flex-1 flex-col justify-between gap-2">
					<ImageUploadInput
						:imageURL="pageStore.activePage?.meta_image"
						label="Meta Image"
						placeholder="Upload Meta Image"
						labelPosition="top"
						description="Recommended size: 1200 x 630 px; Page preview image is used as a fallback if Meta Image is not set"
						@update:imageURL="
							(url: string) => pageStore.updateActivePage('meta_image', url)
						"></ImageUploadInput>
				</div>
			</div>
			<!-- preview -->
			<div class="flex h-fit w-72 flex-shrink-0 flex-col justify-between gap-1">
				<span class="text-sm text-ink-gray-7">Social Preview</span>
				<div class="flex flex-1 flex-col rounded border border-outline-gray-2">
					<img
						:src="pageStore.activePage?.meta_image || pageStore.activePage?.preview"
						alt=""
						class="h-40 w-full rounded-t object-cover" />
					<div class="flex flex-1 flex-col gap-1 border-t border-outline-gray-2 p-2">
						<span class="text-base text-ink-gray-6">{{ pageStore.activePage?.route }}</span>
						<span class="mt-2 text-base font-medium text-ink-gray-9">
							{{ pageStore.activePage?.page_title }}
						</span>
						<span class="line-clamp-3 text-base leading-5 text-ink-gray-6">
							{{ pageStore.activePage?.meta_description }}
						</span>
					</div>
				</div>
			</div>
		</div>
		<hr class="w-full border-outline-gray-2" />
		<div class="flex w-full flex-col gap-5">
			<BuilderInput
				type="text"
				label="Canonical URL"
				description="Optional. Set this to specify a preferred version of this page for search engines."
				placeholder="https://example.com/preferred-page-url"
				:modelValue="pageStore.activePage?.canonical_url"
				:hideClearButton="true"
				@update:modelValue="(val: string) => pageStore.updateActivePage('canonical_url', val)" />
		</div>
	</div>
</template>
<script setup lang="ts">
import ImageUploadInput from "@/components/ImageUploadInput.vue";
import usePageStore from "@/stores/pageStore";
const pageStore = usePageStore();
</script>
