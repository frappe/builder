<template>
	<div
		v-if="installation"
		class="rounded-lg flex flex-col gap-2.5 border border-outline-gray-2 bg-surface-base p-3">
		<div class="flex items-start gap-2.5">
			<img
				v-if="installation.icon"
				:src="installation.icon"
				class="mt-0.5 size-5 shrink-0 object-contain"
				alt=""
				aria-hidden="true" />
			<span v-else class="lucide-plug mt-0.5 size-5 shrink-0 text-ink-gray-6" aria-hidden="true" />
			<div class="flex min-w-0 flex-col gap-0.5">
				<div class="flex min-w-0 items-center gap-1.5">
					<span class="truncate text-sm font-medium text-ink-gray-9">{{ installation.label }}</span>
					<PluginStatusBadge :plugin="installation" />
				</div>
				<span v-if="installation.description" class="text-p-xs text-ink-gray-6">
					{{ installation.description }}
				</span>
			</div>
		</div>
		<PluginDraftActions :plugin="installation" />
	</div>
	<p v-else class="text-p-xs italic text-ink-gray-5">This plugin was removed.</p>
</template>

<script setup lang="ts">
import PluginDraftActions from "@/components/LeftPanelTabs/Plugins/PluginDraftActions.vue";
import PluginStatusBadge from "@/components/LeftPanelTabs/Plugins/PluginStatusBadge.vue";
import { installations } from "@/data/plugins";
import { computed } from "vue";

/** The card reads the live installation list, so a Share from the Plugins panel shows here too. */
const props = defineProps<{ plugin: string }>();

const installation = computed(() => installations.value.find((row) => row.name === props.plugin));
</script>
