<template>
	<div class="flex flex-col gap-5">
		<div class="flex gap-3">
			<Input
				label="Homepage"
				:show-input-as-option="true"
				:model-value="builderSettings.doc?.home_page"
				:options="routeOptions"
				@update:model-value="
					(val: string) => {
						builderStore.updateBuilderSettings('home_page', val);
					}
				"></Input>
			<Input
				type="text"
				label="Language"
				description="Default HTML lang code (e.g., en, es, fr)"
				placeholder="en"
				:model-value="builderSettings.doc?.default_language || 'en'"
				@update:model-value="
					(val: string) => {
						builderStore.updateBuilderSettings('default_language', val);
					}
				"></Input>
		</div>
		<hr class="w-full border-outline-gray-2" />
		<div class="flex flex-col justify-between gap-5">
			<span class="text-lg-semibold text-ink-gray-9">Favicon</span>
			<div class="flex flex-1 gap-5">
				<div
					class="flex items-center justify-center rounded border border-outline-gray-1 bg-surface-gray-2 px-20 py-5">
					<img
						:src="builderSettings.doc?.favicon || '/assets/builder/images/frappe_black.png'"
						alt="Site Favicon"
						class="size-6 rounded" />
				</div>
				<div class="flex flex-1 flex-col gap-2">
					<ImageUploader
						label="Favicon"
						image_type="image/ico"
						:image_url="builderSettings.doc?.favicon"
						@upload="(url: string) => builderStore.updateBuilderSettings('favicon', url)"
						@remove="() => builderStore.updateBuilderSettings('favicon', '')" />
					<span class="text-p-sm text-ink-gray-6">
						Appears next to the title in your browser tab. Recommended size is 32x32 px in PNG or ICO
					</span>
				</div>
			</div>
		</div>
		<hr class="w-full border-outline-gray-2" />
		<Switch
			size="sm"
			label="Enable View Tracking"
			description="Track the number of views on each page of your website"
			:model-value="Boolean(websiteSettings.doc?.enable_view_tracking)"
			@update:model-value="
				(val: Boolean) => {
					websiteSettings.setValue.submit({
						enable_view_tracking: val,
					});
				}
			" />
		<Switch
			size="sm"
			label="Auto convert images to WebP"
			description="All the images uploaded via Builder will be converted to WebP for better page performance"
			:model-value="Boolean(builderSettings.doc?.auto_convert_images_to_webp)"
			@update:model-value="
				(val: Boolean) => builderStore.updateBuilderSettings('auto_convert_images_to_webp', val)
			" />
		<Switch
			size="sm"
			label="Disable Auto Dark Mode"
			description="Prevent the site from automatically switching to dark mode"
			:model-value="Boolean(builderSettings.doc?.disable_auto_dark_mode)"
			@update:model-value="
				(val: Boolean) => builderStore.updateBuilderSettings('disable_auto_dark_mode', val)
			" />
	</div>
</template>
<script setup lang="ts">
import { allWebPages } from "@/data/allWebPages";
import { builderSettings } from "@/data/builderSettings";
import { websiteSettings } from "@/data/websiteSettings";
import useBuilderStore from "@/stores/builderStore";
import { BuilderPage } from "@/types/doctypes";
import { Switch } from "frappe-ui";
import { computed } from "vue";
import ImageUploader from "../Controls/ImageUploader.vue";

const builderStore = useBuilderStore();

const routeOptions = computed(() => {
	return allWebPages.data
		?.filter((page: BuilderPage) => {
			return page.route && !page.dynamic_route;
		})
		.map((page: BuilderPage) => {
			return {
				value: `/${page.route}`,
				label: `/${page.route}`,
			};
		});
});
</script>
