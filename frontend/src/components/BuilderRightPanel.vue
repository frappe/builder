<template>
	<div
		:style="{
			width: `${store.builderLayout.rightPanelWidth}px`,
		}">
		<div class="relative min-h-full">
			<PanelResizer
				:dimension="store.builderLayout.rightPanelWidth"
				side="left"
				@resize="(width) => (store.builderLayout.rightPanelWidth = width)"
				:min-dimension="275"
				:max-dimension="400" />
			<div class="sticky top-0 z-[12] flex w-full bg-surface-white px-2 text-base">
				<button
					v-for="tab of ['Properties', 'Script'] as RightSidebarTabOption[]"
					:key="tab"
					class="mx-2 flex-1 p-2 py-3"
					@click="store.rightPanelActiveTab = tab"
					:class="{
						'border-b-[1px] border-gray-900 dark:border-zinc-500 dark:text-zinc-300':
							store.rightPanelActiveTab === tab,
						'text-gray-700 dark:text-zinc-500': store.rightPanelActiveTab !== tab,
					}">
					{{ tab }}
				</button>
			</div>
			<BlockProperties v-show="store.rightPanelActiveTab === 'Properties'" class="p-4" />
			<PageScript
				class="p-4"
				v-show="store.rightPanelActiveTab === 'Script'"
				:key="store.selectedPage"
				v-if="store.selectedPage && store.activePage"
				:page="store.activePage" />
			<!-- <PageOptions
				class="p-4"
				v-show="store.rightPanelActiveTab === 'Options'"
				:key="store.selectedPage"
				v-if="store.selectedPage && store.activePage"
				:page="store.activePage" /> -->
		</div>
	</div>
</template>
<script setup lang="ts">
import useStore from "@/store";
import BlockProperties from "./BlockProperties.vue";
import PageScript from "./PageScript.vue";
import PanelResizer from "./PanelResizer.vue";
const store = useStore();
</script>
