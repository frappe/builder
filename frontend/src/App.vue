<template>
	<div>
		<router-view v-slot="{ Component }">
			<keep-alive>
				<component :is="Component" />
			</keep-alive>
		</router-view>
		<UseDark attribute="data-theme"></UseDark>
		<FrappeUIProvider />
	</div>
</template>
<script setup lang="ts">
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { UseDark } from "@vueuse/components";
import { useTitle } from "@vueuse/core";
import { FrappeUIProvider, toast } from "frappe-ui";
import { computed, onMounted, provide, watch } from "vue";
import { useRoute } from "vue-router";
import { sessionUser } from "./router";

// do not remove this
const builderStore = useBuilderStore();
const pageStore = usePageStore();
const route = useRoute();

provide("sessionUser", sessionUser);

const title = computed(() => {
	return pageStore.activePage && route.name !== "home"
		? `${pageStore.activePage.page_title || "Untitled"} | Builder`
		: "Frappe Builder";
});

useTitle(title);

onMounted(() => {
	watch(
		() => builderStore.isSiteInReadOnlyMode,
		(readOnly) => {
			if (!readOnly) return;
			toast.warning("Site is in read-only mode", {
				id: "site-read-only-mode",
				duration: Infinity,
				description:
					"Editing is disabled while the site is being updated. Please try again in a few minutes.",
			});
		},
		{ immediate: true },
	);
});
</script>
