<template>
	<div
		class="toolbar border-outline border-outline flex items-center justify-center border-b-[1px] border-outline-gray-1 bg-surface-white px-2 py-1"
		ref="toolbar">
		<div class="absolute left-3 flex items-center gap-5">
			<MainMenu @showSettings="() => (showSettingsDialog = true)"></MainMenu>
			<div class="flex gap-2">
				<Tooltip
					:text="mode.description"
					:hoverDelay="0.6"
					v-for="mode in [
						{ mode: 'select', icon: 'mouse-pointer', description: 'Select (v)' },
						{ mode: 'container', icon: 'square', description: 'Container (c)' },
						{ mode: 'text', icon: 'type', description: 'Text (t)' },
						{ mode: 'image', icon: 'image', description: 'Image (i)' },
					]">
					<BuilderButton
						variant="ghost"
						:icon="mode.icon"
						class="text-ink-gray-7 hover:bg-surface-gray-2 focus:!bg-surface-gray-3 [&[active='true']]:bg-surface-gray-3 [&[active='true']]:text-ink-gray-9"
						@click="() => (builderStore.mode = mode.mode as BuilderMode)"
						:active="builderStore.mode === mode.mode"></BuilderButton>
				</Tooltip>
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
								<FeatherIcon
									name="home"
									class="h-[14px] w-4"
									v-if="pageStore.isHomePage(pageStore.activePage)"></FeatherIcon>
							</Tooltip>
							<Tooltip text="This page has limited access" :hoverDelay="0.6">
								<AuthenticatedUserIcon
									class="size-4 text-ink-amber-3"
									v-if="
										pageStore.activePage?.published && pageStore.activePage?.authenticated_access
									"></AuthenticatedUserIcon>
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
						<FeatherIcon
							name="external-link"
							v-if="pageStore.activePage && pageStore.activePage.published"
							class="h-[14px] w-[14px] !text-gray-700 dark:!text-gray-200"
							@click="pageStore.openPageInBrowser(pageStore.activePage as BuilderPage)"></FeatherIcon>
					</div>
				</template>
				<template #body="{ close }">
					<div
						class="flex w-72 flex-col gap-3 rounded bg-surface-white p-4 shadow-lg"
						v-if="pageStore.activePage">
						<PageOptions v-if="pageStore.activePage" :page="pageStore.activePage"></PageOptions>
					</div>
				</template>
			</Popover>
		</div>
		<div class="absolute right-3 flex items-center gap-4">
			<div class="group flex hover:gap-1">
				<div v-for="[clientId, user] in remoteUsers" :key="clientId">
					<Tooltip :text="user.userName" :hoverDelay="0.6" arrow-class="mb-3">
						<div
							class="ml-[-10px] h-6 w-6 cursor-pointer transition-all group-hover:ml-0"
							@click="emit('followUser', clientId)">
							<img
								v-if="user.userImage"
								class="h-full w-full rounded-full border-2 object-cover shadow-sm transition-all"
								:class="{ 'ring-2 ring-offset-1': followingUserId === clientId }"
								:style="{
									borderColor: user.userColor,
									'--tw-ring-color': followingUserId === clientId ? user.userColor : undefined,
								}"
								:title="user.userName"
								:src="user.userImage" />
							<div
								v-else
								:title="user.userName"
								:style="{
									borderColor: user.userColor,
									'--tw-ring-color': followingUserId === clientId ? user.userColor : undefined,
								}"
								class="grid h-full w-full place-items-center rounded-full border-2 bg-surface-gray-1 text-2xs text-ink-gray-8 shadow-sm transition-all"
								:class="{ 'ring-2 ring-offset-1': followingUserId === clientId }">
								{{ getUserInitials(user.userName) }}
							</div>
						</div>
					</Tooltip>
				</div>
			</div>
			<Badge variant="subtle" theme="orange" v-if="builderStore.readOnlyMode">Read Only</Badge>
			<div class="flex gap-2">
				<Tooltip text="Toggle Dark Mode" :hoverDelay="0.6" arrow-class="mb-3">
					<Button
						variant="ghost"
						@click="() => transitionTheme(toggleDark)"
						:icon="isDark ? 'sun' : 'moon'"></Button>
				</Tooltip>
				<span
					class="text-sm text-ink-gray-3"
					v-if="pageStore.savingPage && pageStore.activePage?.is_template">
					Saving template
				</span>
				<Tooltip text="Settings" :hoverDelay="0.6" arrow-class="mb-3">
					<Button variant="ghost" @click="showSettingsDialog = true" :icon="SettingsGearIcon"></Button>
				</Tooltip>
				<router-link :to="{ name: 'preview', params: { pageId: pageStore.selectedPage } }" title="Preview">
					<Tooltip text="Preview" :hoverDelay="0.6" arrow-class="mb-3">
						<Button variant="ghost" :icon="PlayIcon"></Button>
					</Tooltip>
				</router-link>
			</div>
			<PublishButton :disabled="builderStore.readOnlyMode"></PublishButton>
		</div>
		<Dialog
			:options="{
				title: 'Get Started',
				size: '4xl',
			}"
			v-model="showInfoDialog">
			<template #body-content>
				<iframe
					class="h-[60vh] w-full rounded-sm"
					src="https://www.youtube-nocookie.com/embed/videoseries?si=8NvOFXFq6ntafauO&amp;controls=0&amp;list=PL3lFfCEoMxvwZsBfCgk6vLKstZx204xe3"
					title="Frappe Builder - Get Started"
					frameborder="0"
					allowfullscreen></iframe>
			</template>
		</Dialog>
		<Dialog
			v-model="showSettingsDialog"
			:disableOutsideClickToClose="true"
			class="[&>div>div[id^=headlessui-dialog-panel]]:my-3"
			:options="{
				title: 'Settings',
				size: '5xl',
			}">
			<template #body>
				<BuilderSettings @close="showSettingsDialog = false"></BuilderSettings>
			</template>
		</Dialog>
	</div>
</template>
<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import AuthenticatedUserIcon from "@/components/Icons/AuthenticatedUser.vue";
import PlayIcon from "@/components/Icons/Play.vue";
import SettingsGearIcon from "@/components/Icons/SettingsGear.vue";
import PublishButton from "@/components/PublishButton.vue";
import { webPages } from "@/data/webPage";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { getTextContent } from "@/utils/helpers";
import { UserAwareness } from "@/utils/yjsHelpers";
import { useDark, useToggle } from "@vueuse/core";
import { Badge, Popover, Tooltip } from "frappe-ui";
import { computed, defineAsyncComponent, PropType, ref } from "vue";
import { toast } from "vue-sonner";
import MainMenu from "./MainMenu.vue";
import PageOptions from "./PageOptions.vue";

const BuilderSettings = defineAsyncComponent(() => import("./BuilderSettings.vue"));

defineProps({
	remoteUsers: {
		type: Map as PropType<Map<number, UserAwareness>>,
		default: () => new Map(),
	},
	followingUserId: {
		type: Number as PropType<number | null>,
		default: null,
	},
});

const emit = defineEmits<{
	followUser: [clientId: number];
}>();

const isDark = useDark({
	attribute: "data-theme",
});

const toggleDark = useToggle(isDark);
const builderStore = useBuilderStore();
const pageStore = usePageStore();

const showInfoDialog = ref(false);
const showSettingsDialog = ref(false);

function getUserInitials(name: string | undefined): string {
	if (!name) return "?";
	const parts = name.split(/[\s@._-]+/).filter(Boolean);
	if (parts.length === 0) return "?";
	if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
	return (parts[0][0] + parts[1][0]).toUpperCase();
}

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

const saveAsTemplate = async () => {
	toast.promise(
		webPages.setValue.submit({
			name: pageStore.activePage?.name,
			is_template: true,
		}),
		{
			loading: "Saving as template",
			success: () => {
				pageStore.fetchActivePage(pageStore.selectedPage as string).then((page) => {
					pageStore.activePage = page;
				});
				return "Page saved as template";
			},
		},
	);
};
</script>
