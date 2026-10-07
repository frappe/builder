<template>
	<div class="flex h-full min-h-0 flex-col">
		<!-- A site with no usable key has nothing worth listing, so the setup flow IS
		     the screen until one exists. After that it's reached via "Add provider". -->
		<AISetupFlow v-if="setupMode" :canSkipSetup="configured" :state="setupState" @done="finishSetup" />
		<AIModelList v-else @add-provider="addProvider" />
	</div>
</template>
<script setup lang="ts">
import type { AISetupState } from "@/components/ai/types";
import AIModelList from "@/components/Settings/AIModelList.vue";
import AISetupFlow from "@/components/Settings/AISetupFlow.vue";
import useBuilderStore from "@/stores/builderStore";
import { onMounted, ref } from "vue";

const builderStore = useBuilderStore();
const configured = ref(true);
const setupMode = ref(false);
const setupState = ref<AISetupState | null>(null);

const check = async () => {
	setupState.value = await builderStore.refreshAIState();
	configured.value = !!setupState.value?.configured;
	setupMode.value = !configured.value;
};

const addProvider = () => {
	// providers may have changed in the list since the check, so the flow asks afresh
	setupState.value = null;
	setupMode.value = true;
};

const finishSetup = async () => {
	setupMode.value = false;
	await check();
};

onMounted(check);
</script>
