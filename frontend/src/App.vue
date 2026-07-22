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
import { frappeRequest, FrappeUIProvider, toast } from "frappe-ui";
import { computed, nextTick, onMounted, provide, watch } from "vue";
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
	let readOnlyPoll: number | null = null;
	watch(
		() => builderStore.isSiteInReadOnlyMode,
		(readOnly, wasReadOnly) => {
			if (readOnly) {
				toast.warning("Site is in read-only mode", {
					id: "site-read-only-mode",
					duration: Infinity,
					description:
						"Editing is disabled while the site is being updated. Please try again in a few minutes.",
				});
				readOnlyPoll ??= window.setInterval(() => {
					frappeRequest({ url: "builder.api.is_site_read_only" })
						.then((readOnly: boolean) => (builderStore.isSiteInReadOnlyMode = readOnly))
						.catch(() => {});
				}, 10000);
			} else if (wasReadOnly) {
				if (readOnlyPoll) {
					clearInterval(readOnlyPoll);
					readOnlyPoll = null;
				}
				toast.dismiss("site-read-only-mode");
				toast.success("Site is back online", { description: "You can continue editing." });
				if (pageStore.selectedPage) nextTick(() => pageStore.savePage());
			}
		},
		{ immediate: true },
	);
});
</script>
