<template>
	<div class="flex h-full flex-col items-center gap-5 overflow-y-auto">
		<div class="flex w-full max-w-[500px] gap-4">
			<div class="flex flex-1 flex-col gap-5">
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
				<div class="flex justify-between gap-5">
					<div class="flex flex-1 gap-4">
						<div class="flex flex-1 flex-col gap-2">
							<ImageUploader
								label="Meta Image"
								:image_url="store.activePage?.meta_image"
								@upload="(url: string) => store.updateActivePage('meta_image', url)"
								@remove="() => store.updateActivePage('meta_image', '')" />
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import ImageUploader from "@/components/ImageUploader.vue";
import Input from "@/components/Input.vue";
import InputLabel from "@/components/InputLabel.vue";
import useStore from "@/store";
// check route for page id
const store = useStore();
</script>
