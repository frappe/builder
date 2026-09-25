<template>
	<ContextMenu :options="menu">
		<SidebarItem
			class="[&:has(button:focus-visible)]:focus-ring [&_button]:!outline-none"
			:active="page.name === pageStore.activePage?.name"
			:title="`${page.page_title}\n/${page.route}`"
			@click="openPage(page)">
			<template #prefix>
				<PageStatusDot :page="page" />
			</template>
			<span class="ml-1 flex min-w-0 items-center gap-1.5">
				<span class="truncate text-sm leading-tighter">{{ shortTitle(page) }}</span>
				<span
					v-if="pageStore.isHomePage(page)"
					class="lucide-home size-3 shrink-0 text-ink-gray-4"
					:aria-label="__('Homepage')" />
			</span>
			<template #suffix>
				<span class="mr-2 max-w-24 truncate text-sm text-ink-gray-4">{{ routeLabel }}</span>
			</template>
		</SidebarItem>
	</ContextMenu>
</template>
<script setup lang="ts">
import PageStatusDot from "@/components/PageStatusDot.vue";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/doctypes";
import { ContextMenu, SidebarItem } from "frappe-ui";
import { computed } from "vue";
import { openPage, pageMenu, shortTitle } from "@/utils/pageActions";

const props = defineProps<{
	page: BuilderPage;
	routeLabel: string;
}>();

const pageStore = usePageStore();
const menu = computed(() => pageMenu(props.page));
</script>
