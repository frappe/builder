<template>
	<div class="flex h-[80vh] overflow-hidden">
		<div class="flex w-48 flex-col gap-4 p-5">
			<span class="text-xl font-semibold text-gray-800 dark:text-zinc-200">Settings</span>
			<div class="flex flex-col gap-2">
				<span class="text-base text-gray-700 dark:text-zinc-400">General</span>
				<span class="text-base text-gray-700 dark:text-zinc-400">Meta</span>
				<span class="text-base text-gray-700 dark:text-zinc-400">Robots</span>
				<span class="text-base text-gray-700 dark:text-zinc-400">Analytics</span>
			</div>
		</div>
		<div class="flex h-full flex-1 flex-col gap-5 bg-white p-5 dark:bg-zinc-900">
			<div class="flex justify-between">
				<span class="text-xl font-semibold text-gray-800 dark:text-zinc-200">Page Settings</span>
				<Button icon="x" @click="$emit('close')"></Button>
			</div>
			<div class="flex h-full flex-col gap-5 overflow-y-auto">
				<div class="flex w-full gap-4">
					<div class="flex flex-1 flex-col gap-5">
						<div class="flex gap-4">
							<Input
								type="text"
								label="Page Title"
								:modelValue="store.activePage?.page_title"
								@update:modelValue="(val) => store.updateActivePage('page_title', val)" />
							<Input
								type="text"
								label="Page Route"
								:modelValue="store.activePage?.route"
								@update:modelValue="(val) => store.updateActivePage('route', val)" />
						</div>
						<Input
							type="textarea"
							label="Page Description"
							:modelValue="store.activePage?.meta_description"
							@update:modelValue="(val) => store.updateActivePage('meta_description', val)" />
						<div class="flex justify-between gap-5">
							<div class="flex flex-1 gap-4">
								<div class="flex flex-1 flex-col gap-2">
									<InputLabel>Meta Image</InputLabel>
									<ImageUploader
										:image_url="store.activePage?.meta_image"
										@upload="(url: string) => store.updateActivePage('meta_image', url)"
										@remove="() => store.updateActivePage('meta_image', '')" />
								</div>
								<div class="flex flex-1 flex-col gap-2">
									<InputLabel>Favicon</InputLabel>
									<ImageUploader
										image_type="image/ico"
										:image_url="store.activePage?.favicon"
										@upload="(url: string) => store.updateActivePage('favicon', url)"
										@remove="() => store.updateActivePage('favicon', '')" />
								</div>
							</div>
							<!-- <div class="flex flex-col gap-2">
								<div class="flex flex-col gap-2">
									<InputLabel>Social Preview</InputLabel>
								</div>
								<div class="flex flex-col gap-2">
									<div class="flex items-center justify-between">
										<div
											class="flex h-fit flex-col gap-1 rounded-md border border-gray-100 p-4 dark:border-zinc-800">
											<img
												:src="store.activePage?.meta_image || store.activePage?.preview"
												alt="Favicon Preview"
												class="h-28 rounded" />
											<span class="mt-2 text-base text-blue-600">{{ store.activePage?.page_title }}</span>
											<span class="text-sm italic text-gray-600">
												{{ store.activePage?.meta_description }}
											</span>
										</div>
									</div>
								</div>
							</div> -->
						</div>
					</div>
				</div>
				<hr class="dark:border-zinc-800" />
				<div class="flex flex-col gap-2">
					<div class="flex items-center justify-between">
						<div class="flex flex-col gap-2">
							<span class="text-base dark:text-zinc-200">Unpublish</span>
							<p class="text-sm text-gray-600">Unpublish your page</p>
						</div>
						<Tooltip
							:test="
								store.activePage?.published ? 'Unpublish this page' : 'This page is already unpublished'
							">
							<Button variant="subtle" theme="red" @click="store.unpublishPage()">Unpublish</Button>
						</Tooltip>
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
import { Tooltip } from "frappe-ui";
import { onActivated } from "vue";
// check route for page id
import { useRoute } from "vue-router";
const route = useRoute();
const store = useStore();
const emit = defineEmits(["close"]);

onActivated(() => {
	if (route.params.pageId === store.activePage?.name) return;
	else if (route.params.pageId) {
		store.setActivePage(route.params.pageId as string);
	}
});
</script>
