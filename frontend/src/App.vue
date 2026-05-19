<template>
	<div>
		<router-view v-slot="{ Component }">
			<keep-alive>
				<component :is="Component" />
			</keep-alive>
		</router-view>
		<UseDark attribute="data-theme"></UseDark>
		<ToastProvider />
		<Dialogs></Dialogs>
		<component v-for="dialog in builderStore.appDialogs" :is="dialog"></component>
	</div>
</template>
<script setup lang="ts">
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { UseDark } from "@vueuse/components";
import { useTitle } from "@vueuse/core";
import { Dialogs, ToastProvider } from "frappe-ui";
import { computed, provide } from "vue";
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
</script>
