<template>
	<div
		class="toolbar flex items-center justify-center border-b-[1px] border-outline-gray-1 bg-surface-white px-2 py-1"
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
						class="!text-gray-700 dark:!text-gray-200 hover:dark:bg-zinc-800 focus:dark:bg-zinc-700 [&[active='true']]:bg-gray-100 [&[active='true']]:!text-gray-900 [&[active='true']]:dark:bg-zinc-700 [&[active='true']]:dark:!text-zinc-50"
						@click="() => (store.mode = mode.mode as BuilderMode)"
						:active="store.mode === mode.mode"></BuilderButton>
				</Tooltip>
			</div>
		</div>
		<div>
			<Popover transition="default" placement="bottom" popoverClass="!absolute top-0 !mt-[20px]">
				<template #target="{ togglePopover, isOpen }">
					<div class="flex cursor-pointer items-center gap-2 p-2 text-text-icons-gray-8">
						<div class="flex h-6 items-center text-base text-text-icons-gray-6" v-if="!store.activePage">
							Loading...
						</div>
						<div @click="togglePopover" v-else class="flex items-center gap-1">
							<Tooltip text="This is the homepage for your site" :hoverDelay="0.6">
								<FeatherIcon
									name="home"
									class="h-[14px] w-4"
									v-if="store.isHomePage(store.activePage)"></FeatherIcon>
							</Tooltip>
							<span class="max-w-48 truncate text-base text-text-icons-gray-8">
								{{ store?.activePage?.page_title || "My Page" }}
							</span>
							-
							<span
								class="flex max-w-96 truncate text-base text-text-icons-gray-5"
								v-html="routeString"></span>
						</div>
						<FeatherIcon
							name="external-link"
							v-if="store.activePage && store.activePage.published"
							class="h-[14px] w-[14px] !text-gray-700 dark:!text-gray-200"
							@click="store.openPageInBrowser(store.activePage as BuilderPage)"></FeatherIcon>
					</div>
				</template>
				<template #body="{ close }">
					<div
						class="flex w-72 flex-col gap-3 rounded bg-surface-white p-4 shadow-lg"
						v-if="store.activePage">
						<PageOptions v-if="store.activePage" :page="store.activePage"></PageOptions>
					</div>
				</template>
			</Popover>
		</div>
		<!-- actions -->
		<div class="absolute right-3 flex items-center gap-5">
			<Dialog
				style="z-index: 40"
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
			<div class="group flex hover:gap-1" v-if="store.viewers.length">
				<div v-for="user in store.viewers">
					<Tooltip :text="currentlyViewedByText" :hoverDelay="0.6">
						<div class="ml-[-10px] h-6 w-6 cursor-pointer transition-all group-hover:ml-0">
							<img
								class="h-full w-full rounded-full border-2 border-orange-400 object-cover shadow-sm"
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
			<span class="text-sm dark:text-zinc-300" v-if="store.savingPage && store.activePage?.is_template">
				Saving template
			</span>
			<Tooltip text="Settings" :hoverDelay="0.6">
				<SettingsGearIcon
					@click="showSettingsDialog = true"
					class="h-4 w-4 cursor-pointer text-text-icons-gray-8"></SettingsGearIcon>
			</Tooltip>
			<Dialog
				v-model="showSettingsDialog"
				style="z-index: 40"
				class="[&>div>div[id^=headlessui-dialog-panel]]:my-3"
				:disableOutsideClickToClose="true"
				:options="{
					title: 'Settings',
					size: '5xl',
				}">
				<template #body>
					<Settings @close="showSettingsDialog = false"></Settings>
				</template>
			</Dialog>

			<router-link :to="{ name: 'preview', params: { pageId: store.selectedPage } }" title="Preview">
				<Tooltip text="Preview" :hoverDelay="0.6">
					<PlayIcon class="h-[18px] w-[18px] cursor-pointer text-text-icons-gray-8"></PlayIcon>
				</Tooltip>
			</router-link>
			<BuilderButton
				variant="solid"
				iconLeft="globe"
				@click="
					() => {
						publishing = true;
						store.publishPage().finally(() => (publishing = false));
					}
				"
				class="border-0"
				:class="{
					'bg-surface-gray-7 !text-text-icons-white hover:bg-surface-gray-6':
						!publishing && store.activePage?.draft_blocks,
					'dark:bg-surface-gray-2 dark:text-text-icons-gray-4': !store.activePage?.draft_blocks,
				}"
				:loading="publishing">
				{{ publishing ? "Publishing" : "Publish" }}
			</BuilderButton>
		</div>
	</div>
</template>
<script setup lang="ts">
import PlayIcon from "@/components/Icons/Play.vue";
import SettingsGearIcon from "@/components/Icons/SettingsGear.vue";
import { webPages } from "@/data/webPage";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { Dialog, Tooltip } from "frappe-ui";
import Popover from "frappe-ui/src/components/Popover.vue";
import { computed, ref } from "vue";
import { toast } from "vue-sonner";
import useStore from "../store";
import MainMenu from "./MainMenu.vue";
import PageOptions from "./PageOptions.vue";
import Settings from "./Settings.vue";

const store = useStore();
const publishing = ref(false);
const showInfoDialog = ref(false);
const showSettingsDialog = ref(false);
const toolbar = ref(null);

const currentlyViewedByText = computed(() => {
	const names = store.viewers.map((viewer) => viewer.fullname).map((name) => name.split(" ")[0]);
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
	const route = store.activePage?.route || "/";
	const routeStringToReturn = route.split("/").map((part) => {
		let variable = "";

		if (part.startsWith(":")) {
			variable = part.slice(1);
		} else if (part.startsWith("<")) {
			variable = part.slice(1, -1);
			part = `&lt;${variable}&gt;`;
		}
		if (variable) {
			const previewValue = store.routeVariables[variable];
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
			name: store.activePage?.name,
			is_template: true,
		}),
		{
			loading: "Saving as template",
			success: () => {
				store.fetchActivePage(store.selectedPage as string).then((page) => {
					store.activePage = page;
				});
				return "Page saved as template";
			},
		},
	);
};
</script>
<style>
[data-radix-popper-content-wrapper] {
	margin-top: 15px !important;
	z-index: 20 !important;
}
</style>
