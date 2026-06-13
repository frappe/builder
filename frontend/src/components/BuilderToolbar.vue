<template>
	<div
		class="toolbar border-outline border-outline flex items-center justify-center border-b-[1px] border-outline-gray-1 bg-surface-base px-2 py-1"
		ref="toolbar">
		<div class="absolute left-3 flex items-center gap-4">
			<MainMenu
				@showSettings="
					() => {
						builderStore.settingsActiveTab = 'page_general';
						builderStore.showSettingsDialog = true;
					}
				"
				@showShortcuts="showShortcuts"></MainMenu>
			<div class="flex gap-2">
				<Button
					v-for="mode in [
						{ mode: 'select', icon: 'lucide-mouse-pointer', description: 'Select (v)' },
						{ mode: 'container', icon: 'lucide-square', description: 'Container (c)' },
						{ mode: 'text', icon: 'lucide-type', description: 'Text (t)' },
						{ mode: 'image', icon: 'lucide-image', description: 'Image (i)' },
					]"
					:variant="builderStore.mode === mode.mode ? 'subtle' : 'ghost'"
					:tooltip="mode.description"
					:icon="mode.icon"
					@click="() => (builderStore.mode = mode.mode as BuilderMode)"
					:active="builderStore.mode === mode.mode"></Button>
			</div>
		</div>
		<div>
			<Popover placement="bottom" popoverClass="!mt-[20px]">
				<template #target="{ togglePopover, isOpen }">
					<div class="flex cursor-pointer items-center gap-2 p-2 text-ink-gray-8">
						<div class="flex h-6 items-center text-base text-ink-gray-6" v-if="!pageStore.activePage">
							Loading...
						</div>
						<div @click="togglePopover" v-else class="flex items-center gap-1">
							<Tooltip text="This is the homepage for your site" :hoverDelay="0.6">
								<span
									class="lucide-home h-[14px] w-4"
									aria-hidden="true"
									v-if="pageStore.isHomePage(pageStore.activePage)" />
							</Tooltip>
							<Tooltip text="This page has limited access" :hoverDelay="0.6">
								<span
									class="lucide-shield-user size-4 text-ink-amber-6"
									v-if="pageStore.activePage?.published && pageStore.activePage?.authenticated_access" />
							</Tooltip>
							<span
								class="max-w-48 truncate text-base text-ink-gray-8"
								:title="pageStore?.activePage?.page_title || 'My Page'">
								{{ pageStore?.activePage?.page_title || "My Page" }}
							</span>
							-
							<span
								class="max-w-96 truncate text-base text-ink-gray-5"
								v-html="routeString"
								:title="getTextContent(routeString)"></span>
						</div>
						<span
							class="lucide-external-link h-[14px] w-[14px] !text-gray-700 dark:!text-gray-200"
							aria-hidden="true"
							v-if="pageStore.activePage && pageStore.activePage.published"
							@click="pageStore.openPageInBrowser(pageStore.activePage as BuilderPage)" />
					</div>
				</template>
				<template #body="{ close }">
					<div
						class="flex w-72 flex-col gap-3 rounded bg-surface-base p-4 shadow-lg"
						v-if="pageStore.activePage">
						<PageOptions v-if="pageStore.activePage"></PageOptions>
					</div>
				</template>
			</Popover>
		</div>
		<div class="absolute right-3 flex items-center gap-4">
			<div class="group flex hover:gap-1" v-if="builderStore.viewers.length">
				<div v-for="user in builderStore.viewers">
					<Tooltip :text="currentlyViewedByText" :hoverDelay="0.6" arrow-class="mb-3">
						<div class="ml-[-10px] h-6 w-6 cursor-pointer transition-all group-hover:ml-0">
							<img
								class="h-full w-full rounded-full border-2 border-orange-400 object-cover shadow-sm"
								:title="user.fullname"
								:src="user.image"
								v-if="user.image" />
							<div
								v-else
								:title="user.fullname"
								class="grid h-full w-full place-items-center rounded-full border-2 border-orange-400 bg-gray-400 text-sm text-gray-700 shadow-sm">
								{{ user.fullname.charAt(0) }}
							</div>
						</div>
					</Tooltip>
				</div>
			</div>
			<div class="flex items-center gap-2" v-if="builderStore.readOnlyMode">
				<Badge variant="subtle" theme="orange">
					{{ pageStore.activePage?.is_template ? "Template" : "Read Only" }}
				</Badge>
				<Button
					v-if="pageStore.activePage?.is_template && pageStore.activePage?.template_group"
					size="sm"
					variant="subtle"
					@click="duplicateToEdit">
					Duplicate to edit
				</Button>
			</div>
			<div class="flex items-center gap-2">
				<Tooltip v-if="builderStore.isAIEnabled" text="Generate with AI" :hoverDelay="0.6" arrow-class="mb-3">
					<Button
						variant="ghost"
						@click="openAIGenerator"
						:icon="SparklesIcon"
						:disabled="builderStore.readOnlyMode"></Button>
				</Tooltip>
				<!-- <Tooltip text="Toggle Dark Mode" :hoverDelay="0.6" arrow-class="mb-3">
					<Button
						variant="ghost"
						@click="() => transitionTheme(toggleDark)"
						:icon="isDark ? 'lucide-sun' : 'lucide-moon'"></Button>
				</Tooltip> -->
				<span
					class="text-sm text-ink-gray-3"
					v-if="pageStore.savingPage && pageStore.activePage?.is_template">
					Saving template
				</span>
				<ComponentUpdates />
				<Tooltip text="Settings" :hoverDelay="0.6" arrow-class="mb-3">
					<Button variant="ghost" @click="openSettings" :icon="SettingsGearIcon"></Button>
				</Tooltip>
				<router-link :to="{ name: 'preview', params: { pageId: pageStore.selectedPage } }" title="Preview">
					<Tooltip text="Preview" :hoverDelay="0.6" arrow-class="mb-3">
						<Button variant="ghost" :icon="PlayIcon"></Button>
					</Tooltip>
				</router-link>
			</div>
			<PublishButton
				v-if="!(builderStore.readOnlyMode && pageStore.activePage?.is_template)"
				:disabled="builderStore.readOnlyMode"></PublishButton>
		</div>
		<Dialog title="Get Started" size="4xl" v-model="showInfoDialog">
			<template #default>
				<iframe
					class="h-[60vh] w-full rounded-sm"
					src="https://www.youtube-nocookie.com/embed/videoseries?si=8NvOFXFq6ntafauO&amp;controls=0&amp;list=PL3lFfCEoMxvwZsBfCgk6vLKstZx204xe3"
					title="Frappe Builder - Get Started"
					frameborder="0"
					allowfullscreen></iframe>
			</template>
		</Dialog>
		<Dialog v-model="builderStore.showSettingsDialog" :dismissable="false" size="5xl" bare>
			<template #default>
				<DialogTitle class="sr-only">Builder Settings</DialogTitle>
				<DialogDescription class="sr-only">
					Configure page and global settings for this project.
				</DialogDescription>
				<BuilderSettings
					:initial-tab="builderStore.settingsActiveTab"
					@close="builderStore.showSettingsDialog = false"></BuilderSettings>
			</template>
		</Dialog>
	</div>
</template>
<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import PlayIcon from "@/components/Icons/Play.vue";
import SettingsGearIcon from "@/components/Icons/SettingsGear.vue";
import ComponentUpdates from "@/components/ComponentUpdates.vue";
import PublishButton from "@/components/PublishButton.vue";
import router from "@/router";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/doctypes";
import { getTextContent } from "@/utils/helpers";
import { useDark, useToggle } from "@vueuse/core";
import { Badge, createResource, Popover, toast, Tooltip } from "frappe-ui";
import { DialogDescription, DialogTitle } from "reka-ui";
import { computed, defineAsyncComponent, inject, ref } from "vue";
import SparklesIcon from "~icons/lucide/sparkles";
import MainMenu from "./MainMenu.vue";
import PageOptions from "./PageOptions.vue";

const BuilderSettings = defineAsyncComponent(() => import("./BuilderSettings.vue"));

const isDark = useDark({
	attribute: "data-theme",
});

const toggleDark = useToggle(isDark);
const builderStore = useBuilderStore();
const pageStore = usePageStore();

const showInfoDialog = ref(false);
const showShortcuts = inject<() => void>("showShortcuts", () => {});

const openAIGeneratorFn = inject<(() => void) | undefined>("showAIGenerator", undefined);

const openAIGenerator = (e: MouseEvent) => {
	(e.currentTarget as HTMLElement)?.blur();
	if (openAIGeneratorFn) {
		openAIGeneratorFn();
	} else {
		toast.error("AI Generator is not available");
	}
};

const openSettings = (e: MouseEvent) => {
	(e.currentTarget as HTMLElement)?.blur();
	builderStore.settingsActiveTab = "page_general";
	builderStore.showSettingsDialog = true;
};

const currentlyViewedByText = computed(() => {
	const names = builderStore.viewers.map((viewer) => viewer.fullname).map((name) => name.split(" ")[0]);
	const count = names.length;
	if (count === 0) {
		return "";
	} else if (count === 1) {
		return `${names[0]}`;
	} else if (count === 2) {
		return `${names.join(" & ")}`;
	} else {
		return `${names.slice(0, 2).join(", ")} & ${count - 2} others`;
	}
});

declare global {
	interface Document {
		startViewTransition(callback: () => void): void;
	}
}

const routeString = computed(() => {
	const route = pageStore.activePage?.route || "/";
	const routeStringToReturn = route.split("/").map((part) => {
		let variable = "";

		if (part.startsWith(":")) {
			variable = part.slice(1);
		} else if (part.startsWith("<")) {
			variable = part.slice(1, -1);
			part = `&lt;${variable}&gt;`;
		}
		if (variable) {
			const previewValue = pageStore.routeVariables[variable];
			return `<span class="${
				previewValue ? "bg-purple-100 dark:bg-purple-900" : "bg-gray-100 dark:bg-gray-800"
			} rounded-sm px-[5px] pb-[2px] text-sm">${previewValue || part}</span>`;
		} else {
			return part;
		}
	});
	return routeStringToReturn.join("/");
});

const transitionTheme = (toggleDark: () => void) => {
	if (document.startViewTransition && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
		document.startViewTransition(() => {
			toggleDark();
		});
	} else {
		toggleDark();
	}
};

const duplicateToEdit = async () => {
	toast.promise(
		createResource({
			url: "builder.api.create_page_from_template",
		})
			.submit({ template_page: pageStore.activePage?.name })
			.then((newPageName: string) => {
				router.push({ name: "builder", params: { pageId: newPageName }, force: true });
				pageStore.setPage(newPageName);
			}),
		{
			loading: "Creating an editable copy...",
			success: () => "Page created",
			error: () => "Could not create page from template",
		},
	);
};
</script>
