<template>
	<div class="no-scrollbar flex h-full flex-col items-center gap-6 overflow-y-auto px-[2px]">
		<div class="flex w-full gap-4">
			<div class="flex flex-1 flex-col gap-6">
				<div class="flex gap-5">
					<BuilderInput
						type="text"
						label="页面标题"
						:modelValue="pageStore.activePage?.page_title"
						:hideClearButton="true"
						@update:modelValue="(val: string) => pageStore.updateActivePage('page_title', val)" />
					<BuilderInput
						type="text"
						label="页面路由"
						class="[&>p]:text-p-xs"
						:modelValue="pageStore.activePage?.route"
						:hideClearButton="true"
						@update:modelValue="(val: string) => pageStore.updateActivePage('route', val)" />
				</div>
				<div class="flex flex-col gap-3 text-base">
					<div class="flex">
						<span class="w-20 text-ink-gray-6">URL</span>
						<a class="font-medium text-ink-gray-8 hover:underline" target="_blank" :href="fullURL">
							{{ fullURL }}
						</a>
					</div>
					<div class="flex items-center">
						<span class="w-20 text-ink-gray-6">状态</span>
						<div class="flex items-center gap-2">
							<span class="flex items-center gap-2 text-base text-ink-gray-9">
								<span
									class="lucide-check-circle size-4 text-ink-green-6"
									aria-hidden="true"
									v-if="pageStore.activePage?.published && !pageStore.activePage.authenticated_access" />
								<span
									class="lucide-shield-user size-4 text-ink-amber-6"
									v-else-if="pageStore.activePage?.published && pageStore.activePage?.authenticated_access" />
								<span
									class="lucide-alert-circle size-4 text-ink-gray-4"
									aria-hidden="true"
									v-else-if="!pageStore.activePage?.published" />
								{{
									pageStore.activePage?.published
										? pageStore.activePage?.authenticated_access
											? "受限访问已发布"
											: "已发布"
										: "草稿"
								}}
							</span>

							<Button
								variant="subtle"
								@click="
									pageStore.activePage?.published ? pageStore.unpublishPage() : pageStore.publishPage(false)
								">
								{{ pageStore.activePage?.published ? "取消发布" : "发布" }}
							</Button>
						</div>
					</div>
				</div>
				<!-- favicon -->
				<hr class="w-full border-outline-gray-2" />

				<div class="flex flex-col justify-between gap-5">
					<span class="text-lg-semibold text-ink-gray-9">站点图标</span>
					<div class="flex flex-1 gap-5">
						<div
							class="flex items-center justify-center rounded border border-outline-gray-1 bg-surface-gray-2 px-20 py-5">
							<img
								:src="
									pageStore.activePage?.favicon ||
									builderSettings.doc?.favicon ||
									'/assets/builder/images/frappe_black.png'
								"
								alt="站点图标"
								class="size-6 rounded" />
						</div>
						<div class="flex flex-1 flex-col gap-2">
							<ImageUploader
								label="站点图标"
								image_type="image/ico"
								:image_url="pageStore.activePage?.favicon"
								@upload="(url: string) => pageStore.updateActivePage('favicon', url)"
								@remove="() => pageStore.updateActivePage('favicon', '')" />
							<span class="text-p-sm text-ink-gray-6">
								显示在浏览器标签页标题旁边。推荐尺寸为 32x32 px 的 PNG 或 ICO 格式
							</span>
						</div>
					</div>
				</div>
				<div class="flex flex-col gap-4">
					<hr class="w-full border-outline-gray-2" />
					<!-- homepage -->
					<div class="flex items-center justify-between">
						<div class="flex flex-col gap-2">
							<span class="text-base-medium text-ink-gray-9">主页</span>
							<p class="text-base text-ink-gray-5">将当前页面设为主页</p>
						</div>
						<Button
							variant="subtle"
							@click="
								() => {
									if (pageStore.isHomePage(pageStore.activePage)) {
										builderStore.unsetHomePage();
									} else {
										builderStore.setHomePage(pageStore.activePage?.route as string);
									}
								}
							">
							{{ pageStore.isHomePage(pageStore.activePage) ? "取消主页" : "设为主页" }}
						</Button>
					</div>
					<hr class="w-full border-outline-gray-2" />
					<Switch
						size="sm"
						label="受保护页面"
						:disabled="pageStore.isHomePage(pageStore.activePage)"
						description="仅登录用户可访问此页面"
						:modelValue="Boolean(pageStore.activePage?.authenticated_access)"
						@update:modelValue="(val: Boolean) => pageStore.updateActivePage('authenticated_access', val)" />
					<hr class="w-full border-outline-gray-2" />
					<Switch
						size="sm"
						label="禁用索引"
						description="阻止搜索引擎索引此页面"
						:modelValue="Boolean(pageStore.activePage?.disable_indexing)"
						@update:modelValue="(val: Boolean) => pageStore.updateActivePage('disable_indexing', val)" />
					<template v-if="isDeveloperMode || pageStore.activePage?.is_standard">
						<hr class="w-full border-outline-gray-2" />
						<Switch
							size="sm"
							label="标准页面"
							:disabled="!isDeveloperMode && pageStore.activePage?.is_standard"
							description="将此页面设为可导出到应用的标准页面"
							:modelValue="Boolean(pageStore.activePage?.is_standard)"
							@update:modelValue="handleStandardPageToggle" />
						<hr v-if="pageStore.activePage?.is_standard" class="w-full border-outline-gray-2" />
						<div v-if="pageStore.activePage?.is_standard" class="flex items-center justify-between">
							<div class="flex flex-col gap-2">
								<span class="text-base-medium text-ink-gray-9">应用</span>
								<p class="max-w-xs text-p-sm text-ink-gray-7">为此标准页面选择应用</p>
							</div>
							<div>
								<BuilderInput
									class="w-fit"
									type="select"
									:disabled="!isDeveloperMode && pageStore.activePage?.is_standard"
									:options="appOptions"
									:modelValue="pageStore.activePage?.app"
									@update:modelValue="handleAppChange"></BuilderInput>
							</div>
						</div>
					</template>
					<hr class="w-full border-outline-gray-2" v-if="!pageStore.activePage?.is_standard" />
					<div class="flex items-center justify-between" v-if="!pageStore.activePage?.is_standard">
						<div class="flex flex-col gap-2">
							<span class="text-base-medium text-ink-gray-9">文件夹</span>
							<p class="max-w-xs text-p-sm text-ink-gray-7">设置文件夹以整理您的页面</p>
						</div>
						<div>
							<BuilderInput
								class="w-fit"
								type="select"
								:options="folderOptions"
								:modelValue="pageStore.activePage?.project_folder"
								@update:modelValue="
									(val: string) => pageStore.updateActivePage('project_folder', val)
								"></BuilderInput>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import ImageUploader from "@/components/Controls/ImageUploader.vue";
import builderProjectFolder from "@/data/builderProjectFolder";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { BuilderProjectFolder } from "@/types/doctypes";
import { toTitleCase } from "@/utils/helpers";
import { createResource, Switch, toast } from "frappe-ui";
import { computed } from "vue";

const pageStore = usePageStore();
const builderStore = useBuilderStore();
const isDeveloperMode = computed(() => Boolean(window.is_developer_mode));
const fullURL = computed(
	() => window.location.origin + (pageStore.activePage?.route ? "/" + pageStore.activePage.route : ""),
);

const folderOptions = computed(() => {
	const homeOption = {
		label: "首页",
		value: "",
	};

	const options =
		builderProjectFolder.data?.map((folder: BuilderProjectFolder) => {
			return {
				label: folder.folder_name,
				value: folder.folder_name,
			};
		}) || [];

	return [homeOption, ...options];
});

const installedAppsResource = createResource({
	url: "frappe.core.doctype.module_def.module_def.get_installed_apps",
	cache: "installed_apps",
	auto: true,
	transform: (data: string) => {
		return JSON.parse(data);
	},
});

const appOptions = computed(() => {
	const defaultOption = {
		label: "选择应用",
		value: "",
	};

	const options = (installedAppsResource.data || []).map((app: string) => {
		return {
			label: toTitleCase(app),
			value: app,
		};
	});

	return [defaultOption, ...options];
});

const handleStandardPageToggle = async (val: Boolean) => {
	await pageStore.updateActivePage("is_standard", val);
	notifyStandardPageExport();
};

const handleAppChange = async (val: string) => {
	await pageStore.updateActivePage("app", val);
	notifyStandardPageExport();
};

const notifyStandardPageExport = () => {
	const activePage = pageStore.activePage;

	if (!activePage?.app && activePage?.is_standard) {
		toast.warning("请为此标准页面选择一个应用");
		return;
	}

	if (activePage?.is_standard) {
		const appName = toTitleCase(activePage?.app || "");
		toast.success(`此页面将作为标准页面导出到 ${appName} 应用`);
	}
};
</script>
