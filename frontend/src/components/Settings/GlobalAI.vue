<template>
	<div class="flex flex-col gap-5">
		<div class="flex flex-col gap-2">
			<label class="text-sm text-ink-gray-9">OpenRouter API Key</label>
			<div class="flex items-center gap-2">
				<FormControl
					type="password"
					:modelValue="apiKey"
					@update:modelValue="updateApiKey"
					placeholder="sk-or-v1-…"
					class="flex-1" />
				<Button v-if="apiKey" variant="subtle" @click="testApiKey" :disabled="testing">
					{{ testing ? "Testing..." : "Test Key" }}
				</Button>
			</div>
			<p class="text-xs text-ink-gray-6">
				Get API key from
				<a
					href="https://openrouter.ai/keys"
					target="_blank"
					rel="noopener noreferrer"
					class="text-ink-blue-4 underline">
					openrouter.ai/keys
				</a>
				— supports Claude, Gemini, GPT and more under one key.
			</p>
		</div>
		<div v-if="statusMessage" class="rounded-lg p-3 text-sm" :class="statusClass">
			{{ statusMessage }}
		</div>
	</div>
</template>
<script setup lang="ts">
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import { createResource, FormControl } from "frappe-ui";
import { onMounted, ref } from "vue";

const builderStore = useBuilderStore();

const testing = ref(false);
const statusMessage = ref("");
const statusClass = ref("");
const apiKey = ref("");

const updateApiKey = (value: string) => {
	apiKey.value = value;
	builderStore.updateBuilderSettings("ai_api_key", value);
};

const testApiKey = async () => {
	if (!apiKey.value) return;

	testing.value = true;
	statusMessage.value = "";

	try {
		const result = (await createResource({
			url: "builder.ai_page_generator.test_api_key",
		}).submit()) as { success: boolean; message?: string };

		if (result.success) {
			statusMessage.value = "API key is valid!";
			statusClass.value = "text-ink-green-3 bg-surface-green-1";
		} else {
			statusMessage.value = result.message || "API key test failed";
			statusClass.value = "text-ink-red-3 bg-surface-red-1";
		}
	} catch (error: unknown) {
		statusMessage.value = error instanceof Error ? error.message : "Failed to test API key";
		statusClass.value = "text-ink-red-3 bg-surface-red-1";
	} finally {
		testing.value = false;
		setTimeout(() => {
			statusMessage.value = "";
		}, 5000);
	}
};

onMounted(() => {
	if (builderSettings.doc?.ai_api_key) {
		apiKey.value = builderSettings.doc.ai_api_key;
	}
});
</script>
