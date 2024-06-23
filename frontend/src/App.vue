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
<style>
[id^="headlessui-dialog"] {
	@apply z-30;
}

[id^="headlessui-dialog-panel"] {
	@apply dark:bg-zinc-800;
}

[id^="headlessui-dialog-panel"] > div,
[id^="headlessui-dialog-panel"] p {
	@apply dark:bg-zinc-800;
	@apply dark:text-zinc-50;
}

[id^="headlessui-dialog-panel"] header h3 {
	@apply dark:text-white;
}

[id^="headlessui-dialog-panel"] button svg path {
	@apply dark:fill-white;
}

[id^="headlessui-dialog-panel"] button {
	@apply dark:text-white;
	@apply dark:hover:bg-zinc-700;
	@apply dark:bg-zinc-900;
}

[id^="headlessui-dialog-panel"] input {
	@apply dark:bg-zinc-900;
	@apply dark:border-zinc-800;
	@apply dark:text-gray-50;
}

[id^="headlessui-dialog-panel"] input:focus {
	@apply dark:ring-0;
	@apply dark:border-zinc-700;
}

[id^="headlessui-dialog-panel"] input[type="checkbox"]:checked {
	@apply dark:bg-zinc-700;
}

[id^="headlessui-dialog-panel"] input[type="checkbox"]:focus {
	@apply dark:ring-zinc-700;
	@apply dark:ring-offset-0;
}

[id^="headlessui-dialog-panel"] input[type="checkbox"]:hover {
	@apply dark:bg-zinc-900;
}

[id^="headlessui-dialog-panel"] label > span {
	@apply dark:text-gray-50;
}

[id^="headlessui-dialog"] [data-dialog] {
	@apply dark:bg-black-overlay-800;
}

[id^="headlessui-menu-items"] {
	@apply dark:bg-zinc-800;
	@apply overflow-y-auto;
	-ms-overflow-style: none; /* IE and Edge */
	scrollbar-width: none;
	@apply max-w-60;
	max-height: min(60vh, 24rem);
}
[id^="headlessui-menu-items"] [id^="headlessui-menu-item"] > span {
	@apply truncate;
}
[id^="headlessui-menu-items"] .divide-gray-100 > :not([hidden]) ~ :not([hidden]) {
	@apply dark:border-zinc-700;
}
[id^="headlessui-menu-items"] &::webkit-scrollbar {
	display: none;
}

[id^="headlessui-menu-items"] button {
	@apply dark:text-zinc-200;
	@apply dark:hover:bg-zinc-700;
}

[id^="headlessui-menu-items"] button svg {
	@apply dark:text-zinc-200;
}

[data-sonner-toaster] {
	font-family: "InterVar";
}

[data-sonner-toast][data-styled="true"] {
	@apply dark:bg-zinc-900;
	@apply dark:border-zinc-800;
}
</style>
