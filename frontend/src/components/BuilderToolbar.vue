<template>
	<div
		class="toolbar flex h-14 items-center justify-center bg-white p-2 shadow-sm dark:border-b-[1px] dark:border-gray-800 dark:bg-zinc-900"
		ref="toolbar">
		<div class="absolute left-3 flex items-center">
			<router-link class="flex items-center gap-2" :to="{ name: 'home' }">
				<img src="/builder_logo.png" alt="logo" class="h-7" />
				<h1 class="text-md mt-[2px] font-semibold leading-5 text-gray-800 dark:text-gray-200">Builder</h1>
			</router-link>
		</div>
		<div class="ml-10 flex gap-3">
			<Tooltip
				:text="mode.description"
				:hoverDelay="0.6"
				v-for="mode in [
					{ mode: 'select', icon: 'mouse-pointer', description: 'Select (v)' },
					{ mode: 'text', icon: 'type', description: 'Text (t)' },
					{ mode: 'container', icon: 'square', description: 'Container (c)' },
					{ mode: 'image', icon: 'image', description: 'Image (i)' },
				]">
				<Button
					variant="ghost"
					:icon="mode.icon"
					class="!text-gray-700 dark:!text-gray-200 hover:dark:bg-zinc-800 focus:dark:bg-zinc-700 [&[active='true']]:bg-gray-100 [&[active='true']]:!text-gray-900 [&[active='true']]:dark:bg-zinc-700 [&[active='true']]:dark:!text-zinc-50"
					@click="store.mode = mode.mode as BuilderMode"
					:active="store.mode === mode.mode"></Button>
			</Tooltip>
		</div>
		<div class="absolute right-3 flex items-center gap-5">
			<Dialog
				style="z-index: 40"
				:options="{
					title: 'Get Started',
					size: '4xl',
				}"
				v-model="showDialog">
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

			<Badge
				:variant="'subtle'"
				theme="gray"
				size="md"
				label="Badge"
				class="dark:bg-zinc-600 dark:text-zinc-100"
				v-if="store.isHomePage()">
				Homepage
			</Badge>
			<span class="text-sm dark:text-zinc-300" v-if="store.savingPage && store.activePage?.is_template">
				Saving template
			</span>
			<!-- <button @click="showDialog = true">
				<FeatherIcon
					name="info"
					class="mr-4 h-4 w-4 cursor-pointer text-gray-600 dark:text-gray-400" />
			</button> -->
			<UseDark v-slot="{ isDark, toggleDark }">
				<button @click="transitionTheme(toggleDark)">
					<FeatherIcon
						title="Toggle Theme"
						:name="isDark ? 'moon' : 'sun'"
						class="h-4 w-4 cursor-pointer text-gray-600 dark:text-gray-400" />
				</button>
			</UseDark>
			<router-link
				v-if="store.selectedPage"
				:to="{ name: 'preview', params: { pageId: store.selectedPage } }"
				title="Preview">
				<FeatherIcon name="play" class="h-4 w-4 cursor-pointer text-gray-600 dark:text-gray-400" />
			</router-link>
			<Button
				v-if="!is_developer_mode"
				variant="solid"
				@click="
					() => {
						publishing = true;
						store.publishPage().finally(() => (publishing = false));
					}
				"
				class="border-0 text-xs dark:bg-zinc-800"
				:loading="publishing">
				{{ publishing ? "Publishing" : "Publish" }}
			</Button>
			<div class="flex" v-else>
				<Button
					variant="solid"
					:disabled="store.activePage?.is_template"
					@click="
						() => {
							publishing = true;
							store.publishPage().finally(() => (publishing = false));
						}
					"
					class="rounded-br-none rounded-tr-none border-0 pr-1 text-xs dark:bg-zinc-800"
					:loading="publishing">
					{{ publishing ? "Publishing" : "Publish" }}
				</Button>
				<Dropdown
					:options="[
						// { label: 'Publish', onClick: () => publish() },
						{ label: 'Save As Template', onClick: () => saveAsTemplate() },
					]"
					size="sm"
					class="flex-1 [&>div>div>div]:w-full"
					placement="right">
					<template v-slot="{ open }">
						<Button
							variant="solid"
							@click="open"
							:disabled="store.activePage?.is_template"
							icon="chevron-down"
							class="!w-6 justify-start rounded-bl-none rounded-tl-none border-0 pr-0 text-xs dark:bg-zinc-800"></Button>
					</template>
				</Dropdown>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import { webPages } from "@/data/webPage";
import { UseDark } from "@vueuse/components";
import { Badge, Dialog, Dropdown, Tooltip } from "frappe-ui";
import { computed, ref } from "vue";
import { toast } from "vue-sonner";
import useStore from "../store";

const store = useStore();
const publishing = ref(false);
const showDialog = ref(false);
const toolbar = ref(null);

const is_developer_mode = window.is_developer_mode;

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

const transitionTheme = (toggleDark: () => void) => {
	if (document.startViewTransition && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
		document.startViewTransition(() => {
			toggleDark();
		});
	} else {
		toggleDark();
	}
};

const publish = () => {
	publishing.value = true;
	store.publishPage().finally(() => (publishing.value = false));
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
