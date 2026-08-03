<template>
	<div class="flex flex-col gap-5">
		<div class="flex gap-3">
			<Input
				label="主页"
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
				label="语言"
				description="默认 HTML lang 代码（例如 en, es, fr）"
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
			<span class="text-lg-semibold text-ink-gray-9">站点图标</span>
			<div class="flex flex-1 gap-5">
				<div
					class="flex items-center justify-center rounded border border-outline-gray-1 bg-surface-gray-2 px-20 py-5">
					<img
						:src="builderSettings.doc?.favicon || '/assets/builder/images/frappe_black.png'"
						alt="站点图标"
						class="size-6 rounded" />
				</div>
				<div class="flex flex-1 flex-col gap-2">
					<ImageUploader
						label="站点图标"
						image_type="image/ico"
						:image_url="builderSettings.doc?.favicon"
						@upload="(url: string) => builderStore.updateBuilderSettings('favicon', url)"
						@remove="() => builderStore.updateBuilderSettings('favicon', '')" />
					<span class="text-p-sm text-ink-gray-6">
						显示在浏览器标签页标题旁边。推荐尺寸为 32x32 px 的 PNG 或 ICO 格式
					</span>
				</div>
			</div>
		</div>
		<hr class="w-full border-outline-gray-2" />
		<Switch
			size="sm"
			label="启用浏览量统计"
			description="统计网站每个页面的浏览次数"
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
			label="自动将图片转换为 WebP"
			description="通过 Builder 上传的所有图片都会转换为 WebP 以提升页面性能"
			:model-value="Boolean(builderSettings.doc?.auto_convert_images_to_webp)"
			@update:model-value="
				(val: Boolean) => builderStore.updateBuilderSettings('auto_convert_images_to_webp', val)
			" />
		<Switch
			size="sm"
			label="禁用自动暗色模式"
			description="阻止站点自动切换到暗色模式"
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
