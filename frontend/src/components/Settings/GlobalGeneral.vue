<template>
	<div class="flex flex-col gap-5">
		<InlineInput
			type="autocomplete"
			label="Set Homepage"
			:showInputAsOption="true"
			class="w-1/2"
			:modelValue="builderSettings.doc?.home_page"
			@update:modelValue="
				(val) => {
					store.updateBuilderSettings('home_page', val);
				}
			"
			:options="routeOptions"></InlineInput>
		<hr class="border-surface-gray-2 w-full" />
		<div class="flex flex-col justify-between gap-5">
			<span class="text-lg font-semibold text-ink-gray-9">Favicon</span>
			<div class="flex flex-1 gap-5">
				<div class="flex items-center justify-center rounded border border-outline-gray-1 px-20 py-5">
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
						@upload="(url: string) => store.updateBuilderSettings('favicon', url)"
						@remove="() => store.updateBuilderSettings('favicon', '')" />
					<span class="text-p-sm text-ink-gray-6">
						Appears next to the title in your browser tab. Recommended size is 32x32 px in PNG or ICO
					</span>
				</div>
			</div>
		</div>
		<hr class="border-surface-gray-2 w-full" />
		<Switch
			size="sm"
			label="Enable View Tracking"
			description="Track the number of views on each page of your website"
			:modelValue="Boolean(websiteSettings.doc?.enable_view_tracking)"
			@update:modelValue="
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
			:modelValue="Boolean(builderSettings.doc?.auto_convert_images_to_webp)"
			@update:modelValue="
				(val: Boolean) => store.updateBuilderSettings('auto_convert_images_to_webp', val)
			" />
	</div>
</template>
<script setup lang="ts">
import InlineInput from "@/components/Controls/InlineInput.vue";
import Switch from "@/components/Controls/Switch.vue";
import { builderSettings } from "@/data/builderSettings";
import { webPages } from "@/data/webPage";
import { websiteSettings } from "@/data/websiteSettings";
import useStore from "@/store";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { computed } from "vue";
import ImageUploader from "../Controls/ImageUploader.vue";

const store = useStore();

const routeOptions = computed(() => {
	return webPages.data
		.filter((page: BuilderPage) => {
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
