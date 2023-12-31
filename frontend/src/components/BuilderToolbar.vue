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
					{ mode: 'select', icon: 'mouse-pointer', 'description': 'Select (v)' },
					{ mode: 'text', icon: 'type', 'description': 'Text (t)' },
					{ mode: 'container', icon: 'square', 'description': 'Container (c)' },
					{ mode: 'image', icon: 'image', 'description': 'Image (i)' },
				] as { 'mode': BuilderMode; 'icon': string, 'description': string }[]">
				<Button
					variant="ghost"
					:icon="mode.icon"
					class="!text-gray-700 dark:!text-gray-200 hover:dark:bg-zinc-800 focus:dark:bg-zinc-700 [&[active='true']]:bg-gray-100 [&[active='true']]:!text-gray-900 [&[active='true']]:dark:bg-zinc-700 [&[active='true']]:dark:!text-zinc-50"
					@click="store.mode = mode.mode"
					:active="store.mode === mode.mode"></Button>
			</Tooltip>
		</div>
		<div class="absolute right-3 flex items-center">
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
			<button @click="showDialog = true">
				<FeatherIcon
					title="Toggle Theme"
					name="info"
					class="mr-4 h-4 w-4 cursor-pointer text-gray-600 dark:text-gray-400" />
			</button>
			<UseDark v-slot="{ isDark, toggleDark }">
				<button @click="transitionTheme(toggleDark)">
					<FeatherIcon
						title="Toggle Theme"
						:name="isDark ? 'moon' : 'sun'"
						class="mr-4 h-4 w-4 cursor-pointer text-gray-600 dark:text-gray-400" />
				</button>
			</UseDark>
			<router-link :to="{ name: 'preview', params: { pageId: store.selectedPage } }" title="Preview">
				<FeatherIcon name="play" class="mr-4 h-4 w-4 cursor-pointer text-gray-600 dark:text-gray-400" />
			</router-link>
			<Button
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
		</div>
	</div>
</template>
<script setup lang="ts">
import { UseDark } from "@vueuse/components";
import { Dialog, Tooltip } from "frappe-ui";
import { ref } from "vue";
import useStore from "../store";

const publishing = ref(false);
const showDialog = ref(false);

declare global {
	interface Document {
		startViewTransition(callback: () => void): void;
	}
}

const store = useStore();
const toolbar = ref(null);
const transitionTheme = (toggleDark: () => void) => {
	if (document.startViewTransition && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
		document.startViewTransition(() => {
			toggleDark();
		});
	} else {
		toggleDark();
	}
};
</script>
<style>
.popover-container > div {
	margin-top: 20px !important;
}
</style>
