<template>
	<div
		class="toolbar flex h-14 items-center justify-center bg-white p-2 shadow-sm dark:border-b-[1px] dark:border-gray-800 dark:bg-zinc-900"
		ref="toolbar">
		<div class="absolute left-3 flex items-center">
			<router-link class="flex items-center gap-2" :to="{ name: 'home' }">
				<img src="/builder_logo.png" alt="logo" class="h-7" />
				<h1 class="text-md font-semibold leading-5 text-gray-800 dark:text-gray-200">Builder</h1>
			</router-link>
		</div>
		<div class="ml-10 flex gap-3">
			<Button
				variant="ghost"
				v-for="mode in [
					{ mode: 'select', icon: 'mouse-pointer' },
					{ mode: 'text', icon: 'type' },
					{ mode: 'container', icon: 'square' },
					{ mode: 'image', icon: 'image' },
					{ mode: 'html', icon: 'code'}
				] as { 'mode': BuilderMode; 'icon': string }[]"
				:icon="mode.icon"
				class="!text-gray-700 dark:!text-gray-200 hover:dark:bg-zinc-800 focus:dark:bg-zinc-700 [&[active='true']]:bg-gray-100 [&[active='true']]:!text-gray-900 [&[active='true']]:dark:bg-zinc-700 [&[active='true']]:dark:!text-zinc-50"
				@click="store.mode = mode.mode"
				:active="store.mode === mode.mode"></Button>
		</div>
		<div class="absolute right-3 flex items-center">
			<UseDark v-slot="{ isDark, toggleDark }">
				<FeatherIcon
					title="Toggle Theme"
					:name="isDark ? 'moon' : 'sun'"
					class="mr-4 h-4 w-4 cursor-pointer text-gray-600 dark:text-gray-400"
					@click="toggleDark()" />
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
import { ref } from "vue";

const publishing = ref(false);

import useStore from "../store";

const store = useStore();
const toolbar = ref(null);
</script>
