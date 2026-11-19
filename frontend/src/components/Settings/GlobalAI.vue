<template>
	<!-- each section is a title, a line under it and, for Bob, its switch on the right -->
	<div class="flex flex-col gap-8">
		<div class="flex items-start justify-between gap-4">
			<div class="flex flex-col gap-1">
				<span class="text-md-semibold text-ink-gray-9">{{ __("Bob") }}</span>
				<span class="text-p-sm text-ink-gray-5">
					{{ __("The AI assistant in the editor. Turn it off to hide Bob for everyone on this site.") }}
				</span>
			</div>
			<Switch
				:aria-label="__('Bob')"
				:model-value="builderStore.isBobOn"
				@update:model-value="(on: boolean) => builderStore.updateBuilderSettings('disable_bob', !on)" />
		</div>
		<ProviderList v-if="builderStore.isBobOn" />
		<div class="flex flex-col gap-3">
			<span class="text-md-semibold text-ink-gray-9">{{ __("Connect Your Agent") }}</span>
			<AgentConnect />
		</div>
	</div>
</template>
<script setup lang="ts">
import AgentConnect from "@/components/Settings/AI/AgentConnect.vue";
import ProviderList from "@/components/Settings/AI/ProviderList.vue";
import useBuilderStore from "@/stores/builderStore";
import { __ } from "@/translation";
import { Switch } from "frappe-ui";

const builderStore = useBuilderStore();
</script>
