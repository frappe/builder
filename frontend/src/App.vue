<template>
	<div>
		<router-view v-slot="{ Component }">
			<keep-alive>
				<component :is="Component" />
			</keep-alive>
		</router-view>
		<UseDark></UseDark>
		<Toaster :theme="isDark ? 'dark' : 'light'" richColors />
		<Dialogs></Dialogs>
	</div>
</template>
<script setup lang="ts">
import { UseDark } from "@vueuse/components";
import { useDark, useTitle } from "@vueuse/core";
import { Dialogs } from "frappe-ui";
import { computed, provide } from "vue";
import { useRoute } from "vue-router";
import { Toaster } from "vue-sonner";
import { sessionUser } from "./router";
import useStore from "./store";

const store = useStore();
const route = useRoute();

provide("sessionUser", sessionUser);

const title = computed(() => {
	return store.activePage && route.name !== "home"
		? `${store.activePage.page_title || "Untitled"} | Builder`
		: "Frappe Builder";
});

useTitle(title);

const isDark = useDark();
</script>
