<template>
	<div class="flex h-full flex-col items-center gap-5 overflow-y-auto">
		<div class="flex w-full max-w-[500px] gap-4">
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
				<div class="flex justify-between gap-5">
					<div class="flex flex-1 gap-4">
						<div class="flex flex-1 flex-col gap-2">
							<ImageUploader
								label="Favicon"
								image_type="image/ico"
								:image_url="store.activePage?.favicon"
								@upload="(url: string) => store.updateActivePage('favicon', url)"
								@remove="() => store.updateActivePage('favicon', '')" />
						</div>
					</div>
				</div>
			</div>
		</div>
		<hr class="w-full max-w-[500px] border-gray-200 dark:border-zinc-800" />
		<div class="flex w-full max-w-[500px] flex-col gap-2">
			<div class="flex items-center justify-between">
				<div class="flex flex-col gap-2">
					<span class="text-base dark:text-zinc-200">Unpublish</span>
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
import ImageUploader from "@/components/ImageUploader.vue";
import Input from "@/components/Input.vue";
import InputLabel from "@/components/InputLabel.vue";
import useStore from "@/store";
import { Tooltip } from "frappe-ui";
// check route for page id
const store = useStore();
</script>
