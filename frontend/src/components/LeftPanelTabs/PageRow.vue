<template>
	<ContextMenu :options="menu">
		<ItemListRow
			role="button"
			tabindex="0"
			class="group cursor-pointer outline-none focus-visible:ring-1 focus-visible:ring-outline-gray-3 data-[state=active]:font-medium data-[state=inactive]:hover:bg-surface-gray-1"
			:active="page.name === pageStore.activePage?.name"
			:title="`${page.page_title}\n/${page.route}`"
			@click="openPage(page)"
			@keydown.enter="openPage(page)">
			<template #prefix>
				<PageStatusDot :page="page" />
			</template>
			<span class="flex min-w-0 items-center gap-1.5">
				<span class="truncate">{{ shortTitle(page) }}</span>
				<span
					v-if="pageStore.isHomePage(page)"
					class="lucide-home size-3 shrink-0 text-ink-gray-4"
					:aria-label="__('Homepage')" />
			</span>
			<template #suffix>
				<span class="max-w-24 truncate text-sm text-ink-gray-4">{{ routeLabel }}</span>
			</template>
		</ItemListRow>
	</ContextMenu>
</template>
<script setup lang="ts">
import PageStatusDot from "@/components/PageStatusDot.vue";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/doctypes";
import { ContextMenu, ItemListRow } from "frappe-ui";
import { computed } from "vue";
import { openPage, pageMenu, shortTitle } from "@/utils/pageActions";

const props = defineProps<{
	page: BuilderPage;
	routeLabel: string;
}>();

const pageStore = usePageStore();
const menu = computed(() => pageMenu(props.page));
</script>
