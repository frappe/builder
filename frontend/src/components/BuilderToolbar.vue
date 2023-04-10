<template>
	<div class="toolbar bg-white p-2 flex justify-center h-14 shadow-sm" ref="toolbar">
		<input type="text" v-model="store.pageName"
			class="border-none rounded-md mt-[5px] h-7 bg-gray-100 dark:bg-zinc-800 text-base focus:ring-gray-400 dark:focus:ring-zinc-700 dark:text-gray-300"
			placeholder="Page Name">
		<div class="mt-[5px] absolute right-3 flex items-center">
			<UseDark v-slot="{ isDark, toggleDark }">
				<FeatherIcon :name="isDark ? 'moon': 'sun'" class="h-4 w-4 text-gray-600 dark:text-gray-400 mr-4 cursor-pointer"
					@click="toggleDark()">
				</FeatherIcon>
			</UseDark>
			<Button appearance="primary" @click="publish" class="text-xs rounded-2xl border-0">
				Preview
			</Button>
		</div>
	</div>
</template>
<script setup>
import { ref } from "vue";
import { UseDark } from "@vueuse/components";
import { createResource } from "frappe-ui";
import useStore from "../store";

const store = useStore();
const toolbar = ref(null);

const activateBreakpoint = (device) => {
	store.builderState.activeBreakpoint = device;
};

const publishWebResource = createResource({
	url: "website_builder.api.publish",
	onSuccess(page) {
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
