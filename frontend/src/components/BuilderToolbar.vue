<template>
	<div class="toolbar flex h-14 justify-center bg-white p-2 shadow-sm" ref="toolbar">
		<router-link class="absolute left-3 mt-2 flex items-center" :to="{ name: 'home' }">
			<img src="/favicon.png" alt="logo" class="h-6" />
			<h1 class="ml-1 text-base font-semibold text-gray-600 dark:text-gray-500">pages</h1>
		</router-link>
		<input
			type="text"
			v-model="store.pageName"
			class="mt-[5px] h-7 rounded-md border-none bg-gray-100 text-base focus:ring-gray-400 dark:bg-zinc-800 dark:text-gray-300 dark:focus:ring-zinc-700"
			placeholder="Page Name" />
		<div class="absolute right-3 mt-[5px] flex items-center">
			<router-link :to="{ name: 'page-settings' }">
				<FeatherIcon
					name="settings"
					class="mr-4 h-4 w-4 cursor-pointer text-gray-600 dark:text-gray-400"></FeatherIcon>
			</router-link>
			<UseDark v-slot="{ isDark, toggleDark }">
				<FeatherIcon
					:name="isDark ? 'moon' : 'sun'"
					class="mr-4 h-4 w-4 cursor-pointer text-gray-600 dark:text-gray-400"
					@click="toggleDark()" />
			</UseDark>
			<Button appearance="primary" @click="publish" class="rounded-2xl border-0 text-xs">Preview</Button>
		</div>
	</div>
</template>
<script setup lang="ts">
import { UseDark } from "@vueuse/components";
import { createResource } from "frappe-ui";
import { ref } from "vue";
import useStore from "../store";

const store = useStore();
const toolbar = ref(null);

const publishWebResource = createResource({
	url: "website_builder.api.publish",
	onSuccess(page: any) {
		// hack
		page.blocks = JSON.parse(page.blocks);
		store.pages[page.name] = page as Page;
		store.pageName = page.page_name;
		window.open(`/${page.route}`, "_blank");
	},
});

const publish = () => {
	publishWebResource.submit({
		blocks: store.getPageData(),
		page_name: store.pageName,
	});
};
</script>
