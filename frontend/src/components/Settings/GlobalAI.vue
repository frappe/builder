<template>
	<div class="flex h-full min-h-0 flex-col">
		<!-- A site with no usable key has nothing worth listing, so the setup flow IS
		     the screen until one exists. After that it's reached via "Add provider". -->
		<AISetupFlow v-if="setupMode" :canSkipSetup="configured" @done="finishSetup" />
		<AIModelList v-else @add-provider="setupMode = true" />
	</div>
</template>
<script setup lang="ts">
import AIModelList from "@/components/Settings/AIModelList.vue";
import AISetupFlow from "@/components/Settings/AISetupFlow.vue";
import { createResource } from "frappe-ui";
import { onMounted, ref } from "vue";

const configured = ref(true);
const setupMode = ref(false);

const check = async () => {
	const state: any = await createResource({ url: "builder.ai.api.ai_setup_state" })
		.submit()
		.catch(() => null);
	configured.value = !!state?.configured;
	setupMode.value = !configured.value;
};

const finishSetup = async () => {
	setupMode.value = false;
	await check();
};

onMounted(check);
</script>
