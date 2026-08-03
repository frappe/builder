<template>
	<div class="no-scrollbar flex h-full w-full flex-col items-center gap-5 overflow-y-auto px-[2px]">
		<div class="flex w-full gap-5">
			<!-- meta -->
			<div class="flex flex-1 flex-col gap-4">
				<div class="flex flex-1 flex-col gap-4">
					<BuilderInput
						type="text"
						label="标题"
						:modelValue="pageStore.activePage?.page_title"
						@update:modelValue="(val: string) => pageStore.updateActivePage('page_title', val)" />
					<BuilderInput
						class="[&>div>textarea]:h-28"
						type="textarea"
						label="描述"
						:modelValue="pageStore.activePage?.meta_description"
						:hideClearButton="true"
						@update:modelValue="(val: string) => pageStore.updateActivePage('meta_description', val)" />
				</div>
				<div class="flex flex-1 flex-col justify-between gap-2">
					<ImageUploadInput
						:modelValue="pageStore.activePage?.meta_image"
						label="社交分享图片"
						placeholder="上传社交分享图片"
						labelPosition="top"
						@update:modelValue="
							(url: string) => pageStore.updateActivePage('meta_image', url)
						"></ImageUploadInput>
				</div>
			</div>
			<!-- preview -->
			<div class="flex h-fit w-72 flex-shrink-0 flex-col justify-between gap-1">
				<span class="text-sm text-ink-gray-7">社交预览</span>
				<div class="flex flex-1 flex-col rounded border border-outline-gray-2">
					<img
						:src="pageStore.activePage?.meta_image || pageStore.activePage?.preview"
						alt=""
						class="h-40 w-full rounded-t object-cover" />
					<div class="flex flex-1 flex-col gap-1 border-t border-outline-gray-2 p-2">
						<span class="text-base text-ink-gray-6">{{ pageStore.activePage?.route }}</span>
						<span class="text-base-medium mt-2 text-ink-gray-9">
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
				label="规范 URL"
				description="可选。设置此项以向搜索引擎指定此页面的首选版本。"
				placeholder="https://example.com/preferred-page-url"
				:modelValue="pageStore.activePage?.canonical_url"
				:hideClearButton="true"
				@update:modelValue="(val: string) => pageStore.updateActivePage('canonical_url', val)" />
			<BuilderInput
				type="text"
				label="语言"
				description="HTML 的语言代码（例如 en, es, fr, de）。未设置时使用默认值。"
				placeholder="en"
				:modelValue="pageStore.activePage?.language"
				:hideClearButton="true"
				@update:modelValue="(val: string) => pageStore.updateActivePage('language', val)" />
		</div>
	</div>
</template>
<script setup lang="ts">
import ImageUploadInput from "@/components/ImageUploadInput.vue";
import usePageStore from "@/stores/pageStore";
const pageStore = usePageStore();
</script>
