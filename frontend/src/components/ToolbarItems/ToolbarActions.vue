<template>
	<div class="flex items-center gap-2">
		<Tooltip v-if="builderStore.isAIEnabled" :text="__('Generate with AI')" :hoverDelay="0.6" :offset="12">
			<Button
				variant="ghost"
				@click="openAIGenerator"
				:icon="SparklesIcon"
				:disabled="builderStore.readOnlyMode"></Button>
		</Tooltip>
		<span class="text-sm text-ink-gray-3" v-if="pageStore.savingPage && pageStore.activePage?.is_template">
			{{ __("Saving template") }}
		</span>
		<ComponentUpdates />
		<Tooltip :text="__('Settings')" :hoverDelay="0.6" :offset="12">
			<Button variant="ghost" @click="openSettings" :icon="SettingsGearIcon"></Button>
		</Tooltip>
		<router-link :to="{ name: 'preview', params: { pageId: pageStore.selectedPage } }" :title="__('Preview')">
			<Tooltip :text="__('Preview')" :hoverDelay="0.6" :offset="12">
				<Button variant="ghost" :icon="PlayIcon"></Button>
			</Tooltip>
		</router-link>
	</div>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import ComponentUpdates from "@/components/ComponentUpdates.vue";
import PlayIcon from "@/components/Icons/Play.vue";
import SettingsGearIcon from "@/components/Icons/SettingsGear.vue";
import useAIStore from "@/stores/aiStore";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { Tooltip } from "frappe-ui";
import SparklesIcon from "~icons/lucide/sparkles";

const builderStore = useBuilderStore();
const pageStore = usePageStore();
const aiStore = useAIStore();

const openAIGenerator = (e: MouseEvent) => {
	(e.currentTarget as HTMLElement)?.blur();
	aiStore.showGenerator();
};

const openSettings = (e: MouseEvent) => {
	(e.currentTarget as HTMLElement)?.blur();
	builderStore.showSettingsDialog = true;
};
</script>
