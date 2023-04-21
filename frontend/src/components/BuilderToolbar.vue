<template>
	<div class="toolbar bg-white p-2 flex justify-center h-14 shadow-sm" ref="toolbar">
		<div class="absolute left-3 flex items-center mt-2">
			<img src="/favicon.png" alt="logo" class="h-6">
			<h1 class="font-semibold text-gray-600 dark:text-gray-500 text-base ml-1">
				pages
			</h1>
		</div>
		<input
			type="text" v-model="store.pageName"
			class="border-none rounded-md mt-[5px] h-7 bg-gray-100 dark:bg-zinc-800 text-base focus:ring-gray-400 dark:focus:ring-zinc-700 dark:text-gray-300"
			placeholder="Page Name">
		<div class="mt-[5px] absolute right-3 flex items-center">
			<UseDark v-slot="{ isDark, toggleDark }">
				<FeatherIcon
					:name="isDark ? 'moon': 'sun'"
					class="h-4 w-4 text-gray-600 dark:text-gray-400 mr-4 cursor-pointer"
					@click="toggleDark()" />
			</UseDark>
			<Button appearance="primary" @click="publish" class="text-xs rounded-2xl border-0">
				Preview
			</Button>
		</div>
	</div>
</template>
<script setup lang="ts">
import { ref } from "vue";
import { UseDark } from "@vueuse/components";
import { createResource } from "frappe-ui";
import useStore from "../store";

const store = useStore();
const toolbar = ref(null);

interface Page {
	name: string;
	page_name: string;
	route: string;
	blocks: string;
}

const publishWebResource = createResource({
	url: "website_builder.api.publish",
	onSuccess(page: Page) {
		// hack
		page.blocks = JSON.parse(page.blocks);
		store.pages[page.name] = page;
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
